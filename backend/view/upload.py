import json
from lib import upload
from model.upload import Upload
from model.user import User
from slim.base.permission import Permissions
from slim.retcode import RETCODE
from slim.support.peewee import PeeweeView
from slim.utils import binhex
from view import route
from view.permissions import permissions_add_all
from view.user import UserMixin


@route('upload')
class UploadView(UserMixin, PeeweeView):
    model = Upload

    @route.interface('POST')
    async def token(self):
        user = self.current_user
        if user:
            if self.current_role in ('user', 'admin', 'superuser'):
                type_name = 'avatar' if self.params.get('is_avatar', False) else None
                return self.finish(RETCODE.SUCCESS, upload.get_token(user.id.hex(), type_name))
        self.finish(RETCODE.FAILED)

    @route.interface('POST')
    async def qn_callback(self):
        ua = self.headers.get('User-Agent', None)
        if not (ua and ua.startswith('qiniu-callback')):
            return self.finish(RETCODE.FAILED)

        auth = self.headers.get('Authorization', None)
        if auth:
            content = str(await self._request.content.read(), 'utf-8')
            if upload.verify_callback(auth, str(self._request.url), content):
                # 鉴权成功，确认为七牛服务器回调
                info = json.loads(content)
                uid = binhex.to_bin(info['user_id'])
                # 说明一下，这个哈希值不是base64 hex等编码，具体比较奇怪看了就知道了
                # 总之因此直接使用了TextField来存放
                key = info['key']
                Upload.new(uid, key, info['size'], info['ext'], info['type_name'], info['image_info'])
                if info['type_name'] == 'avatar':
                    # 更换用户头像
                    u = User.get_by_pk(uid)
                    if u:
                        u.avatar = key
                        u.save()
                return self.finish(RETCODE.SUCCESS, key)

        self.finish(RETCODE.FAILED)

    @classmethod
    def ready(cls):
        pass

    @classmethod
    def permission_init(cls):
        permission: Permissions = cls.permission
        permissions_add_all(permission)
