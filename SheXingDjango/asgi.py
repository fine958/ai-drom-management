"""
ASGI config for SheXingDjango project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import attendance.routing  # 注意：这里我们指向 `attendance` 应用下的路由文件

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SheXingDjango.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            attendance.routing.websocket_urlpatterns  # 稍后创建的文件
        )
    ),
})
