from rest_framework import serializers
from .models import ClockIssue, ClockRecord, Leave
from users.models import User
from .models import Record
from .models import AutoClockSetting

class AutoClockSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoClockSetting
        fields = '__all__'
        read_only_fields = ['counselor', 'created_at', 'updated_at']

class RecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = Record
        fields = '__all__'
        read_only_fields = ['student', 'created_time', 'updated_time']

class ClockIssueSerializer(serializers.ModelSerializer):
    issued_by_name = serializers.CharField(source='issued_by.username', read_only=True)

    class Meta:
        model = ClockIssue
        fields = '__all__'
        read_only_fields = ['issued_by', 'create_time']

class ClockRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    issue_info = ClockIssueSerializer(source='issue', read_only=True)

    class Meta:
        model = ClockRecord
        fields = '__all__'
        read_only_fields = ['student', 'clock_time']

class LeaveSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    approver_name = serializers.CharField(source='approver.username', read_only=True)

    class Meta:
        model = Leave
        fields = '__all__'
        read_only_fields = ['student', 'apply_time', 'update_time', 'approver']


from .models import Notification, NotificationTemplate, UserNotification


class NotificationTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['created_by', 'send_time']

class UserNotificationSerializer(serializers.ModelSerializer):
    notification_title = serializers.CharField(source='notification.title', read_only=True)
    notification_content = serializers.CharField(source='notification.content', read_only=True)
    notification_content_en = serializers.CharField(source='notification.content_en', read_only=True)  # 新增
    notification_send_time = serializers.DateTimeField(source='notification.send_time', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserNotification
        fields = ['id', 'user', 'notification', 'is_read', 'read_time',
                  'is_urged', 'urged_count', 'urged_last_time',
                  'notification_title', 'notification_content', 'notification_content_en','notification_send_time','user_name']  # 加上新字段
        read_only_fields = ['id', 'user', 'notification', 'read_time',
                            'urged_count', 'urged_last_time']


from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    receiver_name = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender', 'created_at', 'is_read']
