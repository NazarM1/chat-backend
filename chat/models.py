from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone
from django.utils.timezone import localtime
from mimetypes import guess_type

# models.py
class CustomUser(AbstractUser):
    # groups = models.ManyToManyField(Group, related_name='customuser_groups', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='customuser_permissions', blank=True)
    status = models.CharField(
        max_length=10,
        choices=[('online', 'Online'), ('offline', 'Offline')],
        default='offline'
    )

class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_rooms')  # مسؤول الغرفة
    members = models.ManyToManyField(CustomUser, related_name='rooms', blank=True)  # الأعضاء المشاركون

    def save(self, *args, **kwargs):
        # احفظ الغرفة أولاً للتأكد من أن لها ID
        super().save(*args, **kwargs)
        # أضف المالك إلى قائمة الأعضاء
        if self.owner and not self.members.filter(id=self.owner.id).exists():
            self.members.add(self.owner)
            
    def __str__(self):
        return self.name

class Message(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)  # يمكن أن تكون الرسالة نصية أو بدون نص
    media = models.FileField(upload_to='chat_media/', blank=True, null=True)  # لتخزين الملفات المرف
    media_type = models.CharField(max_length=20, blank=True, null=True)  # نوع الملف
    timestamp = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        if self.media_type:
            return self.media_type
        return self.content
        
    @property
    def formatted_time(self):
        return localtime(self.timestamp).strftime('%I:%M %p')

    @property
    def is_image(self):
        if self.media:
            mime_type, _ = guess_type(self.media.url)
            return mime_type and mime_type.startswith('image')
        return False

    @property
    def is_video(self):
        if self.media:
            mime_type, _ = guess_type(self.media.url)
            return mime_type and mime_type.startswith('video')
        return False

    @property
    def is_audio(self):
        if self.media:
            mime_type, _ = guess_type(self.media.url)
            return mime_type and mime_type.startswith('audio')
        return False

    @property
    def is_other(self):
        if self.media and not (self.is_image or self.is_video or self.is_audio):
            return self.media.name.split('/')[-1]
        return None

    def save(self, *args, **kwargs):
        # تحديد نوع الوسائط تلقائيًا عند حفظ الرسالة
        if self.media:
            mime_type, _ = guess_type(self.media.url)
            if mime_type:
                if mime_type.startswith('image'):
                    self.media_type = 'image'
                elif mime_type.startswith('video'):
                    self.media_type = 'video'
                elif mime_type.startswith('audio'):
                    self.media_type = 'audio'
                else:
                    self.media_type = 'file'
            else:
                self.media_type = 'file'
        
        super().save(*args, **kwargs)

# 4. نموذج الرسائل غير المقروءة
class UnreadMessage(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # المستخدم الذي لم يقرأ الرسالة
    room = models.ForeignKey(Room, on_delete=models.CASCADE)  # الغرفة التي تحتوي الرسالة
    message = models.ForeignKey(Message, on_delete=models.CASCADE)  # الرسالة غير المقروءة
    status = models.CharField(
        max_length=20,
        choices=[('unread', 'Unread'), ('read', 'Read'),('deliver','deliver')],
        default='unread'  # الحالة الافتراضية: "غير مقروءة"
    )
    timestamp = models.DateTimeField(auto_now_add=True)  # وقت تسجيل الحالة

    def __str__(self):
        return f"Unread Message for {self.user.username} in room {self.room.name} - {self.status}"