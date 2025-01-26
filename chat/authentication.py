from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.timezone import now
from chat.models import CustomUser

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.status != 'online':
            user.status = 'online'
            user.save()
        return user
