import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from .models import *
import base64
import mimetypes
from django.core.files.base import ContentFile
from django.utils.timezone import now
import hashlib

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.token = self.scope['query_string'].decode().split('=')[1]
        try:
            validated_token = UntypedToken(self.token)
            user_id = validated_token["user_id"]
            self.user = await database_sync_to_async(User.objects.get)(id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist):
            await self.close(code=4001)
            return

        self.room_group_name = "chat_all_users"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('content', '')
        media_data = data.get('media', None)
        room_name = data.get('room')

        try:
            room = await database_sync_to_async(Room.objects.get)(name=room_name)
        except Room.DoesNotExist:
            await self.send(json.dumps({'error': 'Room not found'}))
            return

        media_file = None
        media_type = None
        if media_data:
            format, file_data = media_data.split(';base64,')
            mime_type = format.split(':')[1]
            guessed_extension = mimetypes.guess_extension(mime_type) or '.bin'
            file_name = f"{self.user.username}_{room_name}_{int(now().timestamp())}{guessed_extension}"
            media_file = ContentFile(base64.b64decode(file_data), name=file_name)

            if mime_type.startswith('image'):
                media_type = 'image'
            elif mime_type.startswith('video'):
                media_type = 'video'
            elif mime_type.startswith('audio'):
                media_type = 'audio'
            else:
                media_type = 'file'

        message = await database_sync_to_async(Message.objects.create)(
            room=room,
            content=content,
            user=self.user,
            media=media_file
        )

        offline_users = await database_sync_to_async(list)(
            room.members.filter(status='offline').exclude(id=self.user.id).values_list('id', flat=True)
        )
        unread_messages = [
            UnreadMessage(user_id=user_id, room=room, message=message, status='unread')
            for user_id in offline_users
        ]
        await database_sync_to_async(UnreadMessage.objects.bulk_create)(unread_messages)

        media_url = message.media.url if message.media else None

        await self.channel_layer.group_send(
            self.room_group_name, {
                'type': 'chat_message',
                'message': content,
                'media': {
                    'url': media_url,
                    'type': media_type
                },
                'user': {
                    'username': self.user.username,
                    'first_name': self.user.first_name,
                    'last_name': self.user.last_name
                },
                'timestamp': message.formatted_time,
                'room': room_name
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.token = self.scope['query_string'].decode().split('=')[1]
        try:
            validated_token = UntypedToken(self.token)
            user_id = validated_token["user_id"]
            self.user = await database_sync_to_async(User.objects.get)(id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist):
            await self.close(code=4001)
            return

        self.group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event))

    async def notify_online_users(self, event):
        phase_content = event["phase_content"]
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": {
                "phase": phase_content["phase"],
                "forword": phase_content["forword"],
                "fk_room": phase_content['fk_room'],
            }
        }))