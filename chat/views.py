from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from .models import Room, Message, CustomUser
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import *
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.exceptions import NotFound

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            # print(refresh.access_token,'sssssssssssssssssssss')
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)



class RoomListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        token = request.META.get('HTTP_AUTHORIZATION', '').split(' ')[1]
        print(f"Used Access Token: {token}")
    
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

