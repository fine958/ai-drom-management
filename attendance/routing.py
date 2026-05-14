# attendance/routing.py
from django.urls import re_path
from . import consumers

# websocket_urlpatterns 是一个列表，定义了 WebSocket 的路径和处理类
websocket_urlpatterns = [
    re_path(r'ws/asr/$', consumers.ASRConsumer.as_asgi()),
]