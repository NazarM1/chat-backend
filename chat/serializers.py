from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate
from django.utils.timezone import localtime

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials', code='authorization')
        else:
            raise serializers.ValidationError('Must include "username" and "password"', code='authorization')

        attrs['user'] = user
        return attrs

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email']  # قم بإضافة الحقول التي تريد عرضها

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email','first_name','last_name']

class RoomSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()  # حقل إضافي لتحديد ما إذا كان المستخدم هو المالك

    class Meta:
        model = Room
        fields = ['id', 'name', 'owner', 'members', 'is_owner']

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.owner == request.user
        return False

class UnreadMessageSerializer(serializers.ModelSerializer):
    message_data = serializers.SerializerMethodField()
    user_data = serializers.SerializerMethodField()
    room_name = serializers.ReadOnlyField(source='room.name')

    class Meta:
        model = UnreadMessage
        fields = ['id', 'message_data', 'user_data', 'timestamp', 'room_name']

    def get_message_data(self, obj):
        message = obj.message
        return {
            'content': message.content,
            'media': {
                'url': message.media.url if message.media else None,
                'type': message.media_type
            }
        }

    def get_user_data(self, obj):
        user = obj.message.user
        return {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }


class MessageSerializer(serializers.ModelSerializer):
    message_type = serializers.SerializerMethodField()
    user = CustomUserSerializer(read_only=True)  # تأكد من وجود CustomUserSerializer
    formatted_time = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'user', 'room', 'content', 'media', 'timestamp', 
                  'formatted_time', 'message_type', 'media_url']

    def get_message_type(self, obj):
        if obj.is_image:
            return 'image'
        elif obj.is_video:
            return 'video'
        elif obj.is_other:
            return 'file'
        elif obj.content:
            return 'text'
        return 'unknown'

    def get_media_url(self, obj):
        request = self.context.get('request')
        if obj.media and request:
            return request.build_absolute_uri(obj.media.url)
        elif obj.media:
            return obj.media.url  # رابط نسبي إذا لم يتوفر request
        return None

    def get_formatted_time(self, obj):
        return localtime(obj.timestamp).strftime('%I:%M %p')