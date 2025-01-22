from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
import time
from datetime import datetime
from .models import *

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('select_room')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')


@login_required
def room_view(request, room_name):
    room, created = Room.objects.get_or_create(name=room_name)
    messages = Message.objects.filter(room=room).order_by('timestamp')
    # تعديل تنسيق الوقت إلى AM/PM
    for message in messages:
        if message.media:
            print(message.media)
    #     local_time = time.localtime(message.timestamp.timestamp())
    #     message.formatted_time = time.strftime('%I:%M %p', local_time)
    #     message.formatted_time = message.timestamp.strftime('%I:%M %p')
    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'messages': messages
    })


@login_required
def select_room(request):
    # إذا تم إرسال اسم الغرفة، تحقق إذا كانت موجودة أو قم بإنشائها
    if request.method == "POST":
        room_name = request.POST.get("room_name")
        if room_name:
            room, created = Room.objects.get_or_create(name=room_name)
            return redirect("chat", room_name=room.name)
    
    # اجلب جميع الغرف والمستخدمين
    rooms = Room.objects.exclude(name__startswith="private")
    users = CustomUser.objects.all()  # أو User.objects.all() إذا كنت تستخدم نموذج المستخدم الافتراضي
    
    return render(request, "chat/select_room.html", {"rooms": rooms, "users": users})
    

@login_required
def private_chat(request, username):
    # تحقق من وجود المستخدم
    other_user = CustomUser.objects.filter(username=username).first()
    if not other_user:
        return render(request, "error.html", {"error": "User not found."})
    
    # إنشاء اسم غرفة فريد للمحادثة بين المستخدمين
    room_name = f"private_{min(request.user.username, other_user.username)}_{max(request.user.username, other_user.username)}"
    
    # قم بإنشاء الغرفة إذا لم تكن موجودة
    room, created = Room.objects.get_or_create(name=room_name)
    
    return redirect("chat", room_name=room.name)