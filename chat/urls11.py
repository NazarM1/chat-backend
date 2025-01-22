from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('select-room/', views.select_room, name='select_room'),
    path('chat/<str:room_name>/', views.room_view, name='chat'),
    path("private/<str:username>/", views.private_chat, name="private_chat"),
]
