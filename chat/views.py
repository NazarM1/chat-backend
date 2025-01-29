from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from .models import *
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import *
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.exceptions import NotFound
from django.core.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = self.get_user_from_request(request)
            if user:
                # تحديث حالة المستخدم إلى "online"
                user.status = 'online'
                user.save()

                # تحديث حالة الرسائل غير المقروءة إلى "deliver"
                # unread_messages = UnreadMessage.objects.filter(user=user, status='unread')
                # unread_messages.update(status='deliver')

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
        # print(username,'1111111111111111111111')
        user_status = request.data.get('status')
        # print(user_status,"2222222222222222222222222")
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
    # authentication_classes = []
    # permission_classes = []
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()  # إدراج التوكن في القائمة السوداء
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
        print(user,'------------')
        unread_messages = UnreadMessage.objects.filter(user=user, status='unread')

        # تحديث حالة الرسائل إلى "read"
        serializer = UnreadMessageSerializer(unread_messages, many=True)
        # unread_messages.update(status='deliver')
        

        return Response({"unread_messages": serializer.data})

    

class RoomListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        token = request.META.get('HTTP_AUTHORIZATION', '').split(' ')[1]
        # print(f"Used Access Token: {token}")
    
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
        rooms = Room.objects.filter(members=user).exclude(name__startswith="private")
        room_serializer = RoomSerializer(rooms, many=True, context={'request': request})
        print(rooms)
        include_users = request.query_params.get('include_users', 'false').lower() == 'true'

        response_data = {
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

class RoomDetailView(APIView):
    def get(self, request, room_name):
        room = Room.objects.filter(name=room_name).first()
        if not room:
            return Response({"error": "Room not found."}, status=404)

        messages = Message.objects.filter(room=room).order_by('timestamp')
        serializer = MessageSerializer(messages, many=True, context={'request': request})  # تمرير request
        return Response({'room': room.name, 'messages': serializer.data})

