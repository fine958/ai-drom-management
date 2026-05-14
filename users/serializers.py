from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Feedback
from .models import User


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        # 指定要返回的字段，密码等敏感信息不要返回
        fields = ['id', 'username', 'role', 'student_id', 'phone_number', 'avatar',
                  'dorm_building', 'dorm_floor', 'dorm_room', 'major', 'class_name', 'groups']
        read_only_fields = ['id']  # id 只读


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    自定义登录序列化器，支持用 username、student_id、phone_number 登录
    """

    def validate(self, attrs):
        # attrs 是前端传过来的数据，默认包含 'username' 和 'password'
        identifier = attrs.get('username')  # 前端仍用 username 字段传值
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError('需要提供账号和密码')

        # 尝试通过不同字段查找用户
        user = None
        # 1. 按 username 精确查找
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            pass

        # 2. 如果没找到，按 student_id 查找
        if not user:
            try:
                user = User.objects.get(student_id=identifier)
            except User.DoesNotExist:
                pass

        # 3. 如果还没找到，按 phone_number 查找
        if not user:
            try:
                user = User.objects.get(phone_number=identifier)
            except User.DoesNotExist:
                pass

        # 4. 验证用户存在且密码正确
        if user and user.check_password(password):
            # 认证成功，将正确的 username 设置回去，让父类方法正常工作
            attrs['username'] = user.username
            return super().validate(attrs)
        else:
            raise serializers.ValidationError('账号或密码错误')


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'user', 'content', 'content_zh', 'created_at', 'is_resolved', 'reply', 'admin_reply']
        read_only_fields = ['id', 'user', 'created_at', 'content_zh']