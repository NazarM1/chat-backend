from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('login/refresh/', CustomTokenRefreshView.as_view(), name='refresh'),
    path('user/status/', UpdateUserStatusView.as_view(), name='update_user_status'),
    path('unread-messages/', UnreadMessagesView.as_view(), name='unread-messages'),
    path('rooms/', RoomListView.as_view(), name='api_rooms'),
    path('rooms/<int:pk>/', RoomListView.as_view(), name='room-detail'),
    path('rooms/<str:room_name>/', RoomDetailView.as_view(), name='api_room_detail'),
    path("token/logout/", LogoutAPIView.as_view(), name="token_logout"),
    
    ]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
