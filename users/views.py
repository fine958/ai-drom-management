from rest_framework import viewsets, permissions
from .models import User
from .serializers import UserSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework import status
from django.contrib.auth.hashers import check_password
from .models import Feedback
from .serializers import FeedbackSerializer
from dorm.doubao_translation_service import call_translate_api


class UserViewSet(viewsets.ModelViewSet):
    """
    提供用户的增删改查接口
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]   # 需要登录才能访问

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        返回当前登录用户的信息
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='update-profile')
    def update_profile(self, request):
        """
        修改当前登录用户的个人信息
        允许修改的字段：phone_number, dorm_building, dorm_floor, dorm_room, major, class_name
        """
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """
        修改当前登录用户的密码
        请求体：{"old_password": "旧密码", "new_password": "新密码"}
        """
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'detail': '旧密码和新密码都不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证旧密码
        if not check_password(old_password, user.password):
            return Response({'detail': '旧密码错误'}, status=status.HTTP_400_BAD_REQUEST)

        # 设置新密码
        user.set_password(new_password)
        user.save()
        return Response({'detail': '密码修改成功'}, status=status.HTTP_200_OK)


class FeedbackViewSet(viewsets.ModelViewSet):
    """
    反馈视图集
    - 用户只能创建和查看自己的反馈
    - 管理员（辅导员/宿管）可以查看所有反馈并回复
    """
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Feedback.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.role in ['counselor', 'dorm_admin']:
            # 管理员可以查看所有反馈
            return Feedback.objects.all()
        else:
            # 普通用户只能看自己的
            return Feedback.objects.filter(user=user)

    def perform_create(self, serializer):
        content = serializer.validated_data.get('content', '')
        content_zh = ''
        # 如果内容非空，调用翻译服务（如果内容已经是中文，翻译服务也能处理，但会消耗次数）
        # 更好的做法是简单判断是否包含中文字符，如果包含则不翻译
        if content:
            # 简单判断是否包含中文字符（可根据需求调整）
            import re
            if re.search('[\u4e00-\u9fff]', content):
                # 内容已经是中文，不需要翻译
                content_zh = content
            else:
                # 调用翻译服务，将英文（或其他语言）翻译成中文
                result = call_translate_api([content], target_language='zh')
                if result.get('translated_texts'):
                    content_zh = result['translated_texts'][0]
                else:
                    # 翻译失败时记录日志，并将原文作为中文（避免丢失）
                    import logging
                    logging.getLogger(__name__).warning(f"反馈翻译失败: {content[:50]}")
                    content_zh = content
        # 保存反馈，同时存入翻译后的中文
        serializer.save(user=self.request.user, content_zh=content_zh)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


