from django.utils.timezone import now
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from chat.models import CustomUser

class TokenExpiryMiddleware:
    """
    Middleware للتحقق من صلاحية التوكن وتحديث حالة المستخدم إذا انتهت صلاحيته.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تحقق من وجود التوكن
        auth_header = request.headers.get('Authorization', None)
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            jwt_auth = JWTAuthentication()
            try:
                # محاولة التحقق من التوكن
                validated_token = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated_token)
                if user.status != 'online':
                    user.status = 'online'
                    user.save()
            except InvalidToken:
                # إذا انتهت صلاحية التوكن، تحديث حالة المستخدم إلى Offline
                user_id = jwt_auth.get_user_id_from_token(token)
                if user_id:
                    try:
                        user = CustomUser.objects.get(id=user_id)
                        user.status = 'offline'
                        user.save()
                    except CustomUser.DoesNotExist:
                        pass

        response = self.get_response(request)
        return response
