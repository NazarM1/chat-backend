import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from chat import consumers  # قم بتعديل اسم التطبيق إذا لزم الأمر

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path(r"^ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
        ])
    ),
})
