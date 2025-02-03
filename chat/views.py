from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import *
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import *
from rest_framework import status
from rest_framework.exceptions import NotFound
from django.core.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = self.get_user_from_request(request)
            if user:
                user.status = 'online'
                user.save()

        return response

    def get_user_from_request(self, request):
        username = request.data.get('username')
        if username:
            try:
                return CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                pass
        return None

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 401:
            # إذا انتهت صلاحية التوكن، تحديث حالة المستخدم إلى "offline"
            token = request.data.get('refresh')
            if token:
                try:
                    payload = RefreshToken(token).payload
                    user_id = payload.get('user_id')
                    if user_id:
                        user = CustomUser.objects.filter(id=user_id).first()
                        if user:
                            user.status = 'offline'
                            user.save()
                except Exception as e:
                    # تجاهل الأخطاء إذا لم يكن التوكن صالحًا
                    pass

        return response

class UpdateUserStatusView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        user_status = request.data.get('status')
        if username and user_status:
            try:
                user = CustomUser.objects.get(username=username)
                user.status = user_status
                user.save()
                return Response({'message': 'User status updated successfully'}, status=status.HTTP_200_OK)
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Username and status are required'}, status=status.HTTP_400_BAD_REQUEST)
    

class LogoutAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()  
            user = request.user
            if user.is_authenticated:
                user.status = 'offline'
                user.save()
        except Exception as e:
            pass
        return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)

class UnreadMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        unread_messages = UnreadMessage.objects.filter(user=user, status='unread')

        serializer = UnreadMessageSerializer(unread_messages, many=True)
        return Response({"unread_messages": serializer.data})


class UpdateUnreadMessagesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        id = request.data.get('id')
        if id:
            try:
                message = UnreadMessage.objects.get(id=id)
                message.status = 'deliver'
                message.save()
                return Response({'message': 'Unreadmessage status updated successfully'}, status=status.HTTP_200_OK)
            except UnreadMessage.DoesNotExist:
                return Response({'error': 'message not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Username and status are required'}, status=status.HTTP_400_BAD_REQUEST)
class RoomListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
    
        user = request.user
        if pk:  # إذا تم تمرير pk، جلب غرفة واحدة
            try:
                room = Room.objects.get(pk=pk)
                if not room.members.filter(id=user.id).exists():
                    raise PermissionDenied("You are not a member of this room.")
                room_serializer = RoomSerializer(room, context={'request': request})
                return Response({"room": room_serializer.data})
            except Room.DoesNotExist:
                raise NotFound("Room not found.")
        # إذا لم يتم تمرير pk، جلب جميع الغرف التي يكون المستخدم عضوًا فيها
        rooms = Room.objects.filter(members=user)
        room_serializer = RoomSerializer(rooms, many=True, context={'request': request})

        phase_contents = PhaseContent.objects.filter(
            forword=user.roll,  # الشرط: forword == user.roll
            fk_room__in=rooms  # الشرط: الغرفة مرتبطة بالغرف التي يكون المستخدم عضوًا فيها
        ).union(
            PhaseContent.objects.filter(
                forword='all',  # الشرط: forword == 'all'
                fk_room__in=rooms  # الشرط: الغرفة مرتبطة بالغرف التي يكون المستخدم عضوًا فيها
            )
        )
        phase_content_serializer = PhaseContentSerializer(phase_contents, many=True)

        include_users = request.query_params.get('include_users', 'false').lower() == 'true'

        response_data = {
            'phase_contents': phase_content_serializer.data,
            "rooms": room_serializer.data
        }

        if include_users:
            users = CustomUser.objects.all()
            user_serializer = UserSerializer(users, many=True)
            response_data["users"] = user_serializer.data

        return Response(response_data)

    def post(self, request):
        # إنشاء غرفة جديدة
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        # تحديث غرفة
        try:
            room = Room.objects.get(pk=pk)
        except Room.DoesNotExist:
            raise NotFound("Room not found.")

        serializer = RoomSerializer(room, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        # حذف غرفة
        try:
            room = Room.objects.get(pk=pk)
        except Room.DoesNotExist:
            raise NotFound("Room not found.")
        room.delete()
        return Response({"detail": "Room deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



class PhaseContentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phase = request.data.get('phase')
        forword = request.data.get('forword')
        fk_room_id = request.data.get('fk_room')

        if not phase or not forword or not fk_room_id:
            return Response({"error": "phase, forword, and fk_room are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room = Room.objects.get(id=fk_room_id)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

        phase_content = PhaseContent.objects.create(
            phase=phase,
            forword=forword,
            fk_room=room
        )

        # إرسال إشعار عبر WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "notifications",
            {
                "type": "notify_online_users",
                "phase_content": phase_content
            }
        )

        return Response({"status": "success", "phase_content": PhaseContentSerializer(phase_content).data}, status=status.HTTP_201_CREATED)
class RoomDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, room_name):
        room = Room.objects.filter(name=room_name).first()
        if not room:
            return Response({"error": "Room not found."}, status=404)

        messages = Message.objects.filter(room=room).order_by('timestamp')
        unread_messages = UnreadMessage.objects.filter(
            user=request.user, room=room, status='deliver'
        )
        unread_messages.delete()
        serializer = MessageSerializer(messages, many=True, context={'request': request})  # تمرير request
        return Response({'room': room.name, 'messages': serializer.data})

