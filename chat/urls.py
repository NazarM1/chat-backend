from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('rooms/', RoomListView.as_view(), name='api_rooms'),
    path('rooms/<int:pk>/', RoomListView.as_view(), name='room-detail'),
    path('rooms/<str:room_name>/', RoomDetailView.as_view(), name='api_room_detail'),
    ]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
