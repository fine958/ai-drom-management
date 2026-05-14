from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import ClockIssue, ClockRecord, Leave
from .serializers import ClockIssueSerializer, ClockRecordSerializer, LeaveSerializer
from .utils import haversine
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from users.models import User
from .models import Record
from .serializers import RecordSerializer
from .models import AutoClockSetting
from .serializers import AutoClockSettingSerializer
from .models import Notification, NotificationTemplate, UserNotification
from .serializers import NotificationSerializer, NotificationTemplateSerializer, UserNotificationSerializer
from django.core.exceptions import PermissionDenied
from dorm.doubao_translation_service import call_translate_api   # 注意导入路径
from django.db.models import Q

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    通知模板视图集
    - 辅导员、班主任、宿管可以管理模板
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 所有人都可以看到模板？也可以只让有权限的人看，这里简单返回所有
        return NotificationTemplate.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class UserNotificationViewSet(viewsets.ModelViewSet):
    """
    用户通知视图集
    - 用户只能查看自己的通知
    - 支持标记已读、催办
    """
    queryset = Notification.objects.all()
    serializer_class = UserNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserNotification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """标记为已读"""
        user_notification = self.get_object()
        if not user_notification.is_read:
            user_notification.is_read = True
            user_notification.read_time = timezone.now()
            user_notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=True, methods=['post'])
    def urge(self, request, pk=None):
        """催办（增加催办次数）"""
        user_notification = self.get_object()
        user_notification.urged_count += 1
        user_notification.is_urged = True
        user_notification.urged_last_time = timezone.now()
        user_notification.save()
        # 这里可以发送推送，暂时只记录
        return Response({'status': 'urged', 'count': user_notification.urged_count})


class NotificationViewSet(viewsets.ModelViewSet):
    """
    通知管理视图集
    - 只有辅导员、班主任、宿管可以发送通知
    - 所有用户都可以查看自己的通知（通过 UserNotification）
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 返回当前用户发送的通知（管理员可以看自己发的）
        return Notification.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        # 权限检查：只有特定角色可以发送通知
        if self.request.user.role not in ['counselor', 'teacher', 'dorm_admin']:
            raise PermissionDenied('您没有发送通知的权限')

        # 获取原始中文内容
        content_zh = serializer.validated_data.get('content', '')

        # 调用翻译服务，将中文翻译成英文
        content_en = ''
        if content_zh:
            result = call_translate_api([content_zh], target_language='en')
            if result.get('translated_texts'):
                content_en = result['translated_texts'][0]
            else:
                # 翻译失败时记录日志，但不影响通知创建
                import logging
                logging.getLogger(__name__).warning(f"通知内容翻译失败: {content_zh[:50]}")

        # 保存通知，同时存入英文内容
        notification = serializer.save(
            created_by=self.request.user,
            content_en=content_en  # 新增的英文字段
        )

        # 根据范围创建 UserNotification 记录
        self.create_user_notifications(notification)

    def create_user_notifications(self, notification):
        """根据通知范围，创建 UserNotification 记录"""
        send_to = notification.send_to
        users_to_notify = []

        if send_to == 'all':
            # 全体用户
            users_to_notify = User.objects.all()
        elif send_to == 'building':
            # 指定楼栋
            building = notification.target_building
            if building:
                users_to_notify = User.objects.filter(dorm_building=building, role__in=['student', 'teacher', 'counselor'])
        elif send_to == 'class':
            # 指定班级
            class_name = notification.target_class
            if class_name:
                users_to_notify = User.objects.filter(class_name=class_name, role='student')
        elif send_to == 'user':
            # 指定用户（target_user 是外键，单个用户）
            user = notification.target_user
            if user:
                users_to_notify = [user]

        # 批量创建 UserNotification 记录
        for user in users_to_notify:
            UserNotification.objects.get_or_create(user=user, notification=notification)

class AutoClockSettingViewSet(viewsets.ModelViewSet):
    queryset = AutoClockSetting.objects.all()
    serializer_class = AutoClockSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'counselor':
            # 辅导员只能看和修改自己的设置
            return AutoClockSetting.objects.filter(counselor=user)
        else:
            # 其他角色无权查看
            return AutoClockSetting.objects.none()

    def perform_create(self, serializer):
        # 自动关联当前辅导员
        serializer.save(counselor=self.request.user)

class RecordViewSet(viewsets.ModelViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Record.objects.all()
        if user.role == 'student':
            queryset = queryset.filter(student=user)
        elif user.role == 'teacher':
            # 班主任可以看本班学生的备案
            queryset = queryset.filter(student__class_name=user.class_name)
        elif user.role == 'counselor':
            # 辅导员看本楼栋学生的备案
            queryset = queryset.filter(student__dorm_building=user.dorm_building)
        # 宿管科可看所有
        return queryset

    def perform_create(self, serializer):
        # 只有学生可以创建备案
        if self.request.user.role != 'student':
            self.permission_denied(self.request, message='只有学生可以创建备案')
        serializer.save(student=self.request.user)

class ClockIssueViewSet(viewsets.ModelViewSet):
    """
    考勤发布视图集
    - 辅导员可以创建、修改、删除自己发布的考勤
    - 其他角色只能查看（学生可查看当前有效的考勤？这里简单处理：所有角色都可查看所有发布）
    """
    queryset = ClockIssue.objects.all().order_by('-start_time')
    serializer_class = ClockIssueSerializer
    permission_classes = [permissions.IsAuthenticated]  # 需要登录

    def get_permissions(self):
        """
        动态设置权限：只有辅导员可以执行写操作（创建、修改、删除）
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # 写操作需要用户角色为辅导员
            if not self.request.user.role == 'counselor':
                self.permission_denied(self.request, message='只有辅导员可以执行此操作')
        return super().get_permissions()

    def perform_create(self, serializer):
        # 自动设置发布人为当前用户
        serializer.save(issued_by=self.request.user)

class ClockRecordViewSet(viewsets.ModelViewSet):
    """
    打卡记录视图集
    - 学生只能查看自己的打卡记录，只能创建自己的打卡（需验证时间和地点）
    - 辅导员/班主任可以查看所管辖学生的记录
    """
    queryset = ClockRecord.objects.all()
    serializer_class = ClockRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = ClockRecord.objects.all()

        if user.role == 'student':
            # 学生只能看自己的记录
            queryset = queryset.filter(student=user)
        elif user.role == 'teacher':
            # 班主任看自己班级学生的记录（需要学生用户有 class_name 字段）
            # 通过学生关联的班级过滤
            queryset = queryset.filter(student__class_name=user.class_name)
        elif user.role == 'counselor':
            # 辅导员看自己楼栋学生的记录（通过学生 dorm_building）
            queryset = queryset.filter(student__dorm_building=user.dorm_building)
        # 宿管科可看所有

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'student':
            self.permission_denied(self.request, message='只有学生可以打卡')

        # 获取请求数据中的考勤任务ID
        issue_id = self.request.data.get('issue')
        if not issue_id:
            raise serializers.ValidationError({'issue': '考勤任务ID不能为空'})

        try:
            issue = ClockIssue.objects.get(id=issue_id)
        except ClockIssue.DoesNotExist:
            raise serializers.ValidationError({'issue': '考勤任务不存在'})

        # 验证时间
        now = timezone.now()
        print('=' * 50)
        print('当前时间 (now):', now)
        print('考勤开始时间 (issue.start_time):', issue.start_time)
        print('考勤结束时间 (issue.end_time):', issue.end_time)
        print('now < start_time?', now < issue.start_time)
        print('now > end_time?', now > issue.end_time)
        print('=' * 50)

        if now < issue.start_time or now > issue.end_time:
            raise ValidationError('不在考勤时间段内')

        # 验证地点
        # 从请求中获取学生打卡的经纬度（前端通过定位获取）
        location = self.request.data.get('location')
        if not location or not isinstance(location, list) or len(location) != 2:
            raise serializers.ValidationError({'location': '请提供有效的经纬度列表，例如 [经度, 纬度]'})

        distance = haversine(location[0], location[1], issue.location[0], issue.location[1])
        if distance > 200:  # 假设200米范围内
            raise serializers.ValidationError(f'不在考勤范围内，距离{distance:.0f}米')

        # 判断是否迟到（可选逻辑：如果当前时间晚于考勤结束时间？但这里已经在时间内）
        # 简单处理：status 默认为 normal
        status = 'normal'

        serializer.save(student=user, issue=issue, location=location, status=status)

class LeaveViewSet(viewsets.ModelViewSet):
    """
    请假/补卡申请视图集
    - 学生可以创建申请，查看自己的申请
    - 辅导员/班主任可以查看所管辖学生的申请，并进行审批
    """
    queryset = Leave.objects.all()
    serializer_class = LeaveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Leave.objects.all()

        if user.role == 'student':
            queryset = queryset.filter(student=user)
        elif user.role == 'teacher':
            queryset = queryset.filter(student__class_name=user.class_name)
        elif user.role == 'counselor':
            queryset = queryset.filter(student__dorm_building=user.dorm_building)
        # 宿管科可看所有

        return queryset

    def perform_create(self, serializer):
        # 学生创建申请
        if self.request.user.role != 'student':
            self.permission_denied(self.request, message='只有学生可以提交申请')
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        """
        审批申请：辅导员/班主任调用此接口
        请求体：{"action": "approve"} 或 {"action": "reject", "reject_reason": "原因"}
        """
        leave = self.get_object()
        user = request.user

        # 权限检查：只有辅导员或班主任可以审批（且只能审批自己管辖的学生）
        if user.role not in ['counselor', 'teacher']:
            return Response({'detail': '只有辅导员或班主任可以审批'}, status=status.HTTP_403_FORBIDDEN)

        # 如果是班主任，检查学生是否在本班
        if user.role == 'teacher' and leave.student.class_name != user.class_name:
            return Response({'detail': '你只能审批自己班级学生的申请'}, status=status.HTTP_403_FORBIDDEN)

        # 如果是辅导员，检查学生是否在本楼栋
        if user.role == 'counselor' and leave.student.dorm_building != user.dorm_building:
            return Response({'detail': '你只能审批自己楼栋学生的申请'}, status=status.HTTP_403_FORBIDDEN)

        action_type = request.data.get('action')
        if action_type == 'approve':
            leave.status = 'approved'
            leave.approver = user
            leave.reject_reason = ''
        elif action_type == 'reject':
            reject_reason = request.data.get('reject_reason', '')
            if not reject_reason:
                return Response({'detail': '拒绝时必须填写原因'}, status=status.HTTP_400_BAD_REQUEST)
            leave.status = 'rejected'
            leave.reject_reason = reject_reason
            leave.approver = user
        else:
            return Response({'detail': 'action 必须是 "approve" 或 "reject"'}, status=status.HTTP_400_BAD_REQUEST)

        leave.save()
        serializer = self.get_serializer(leave)
        return Response(serializer.data)


from .models import Message
from .serializers import MessageSerializer


class MessageViewSet(viewsets.ModelViewSet):
    """
    用户私信视图集
    - 任何登录用户都可以发送消息（但只能发送给其他用户）
    - 用户只能看到自己发送或接收的消息
    - 不支持修改或删除消息（业务上一般不允许撤回）
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 用户只能看到自己发送或接收的消息
        return Message.objects.filter(Q(sender=user) | Q(receiver=user))

    def perform_create(self, serializer):
        # 自动设置发送者为当前用户
        serializer.save(sender=self.request.user)

    # 可选：获取与某个用户的对话历史
    @action(detail=False, methods=['get'])
    def with_user(self, request):
        other_user_id = request.query_params.get('user_id')
        if not other_user_id:
            return Response({'detail': '请提供 user_id 参数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        messages = Message.objects.filter(
            (Q(sender=user) & Q(receiver=other_user)) |
            (Q(sender=other_user) & Q(receiver=user))
        ).order_by('created_at')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    # attendance/views.py 中的 MessageViewSet 内添加

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        批量标记与某人的所有消息为已读
        请求体：{"user_id": 对方用户ID}
        """
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            return Response({'detail': '请提供 user_id 参数'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 将当前用户作为接收者、来自对方且未读的消息全部标记为已读
        updated_count = Message.objects.filter(
            receiver=request.user,
            sender=other_user,
            is_read=False
        ).update(is_read=True)

        return Response({'detail': f'已将 {updated_count} 条消息标记为已读'})
