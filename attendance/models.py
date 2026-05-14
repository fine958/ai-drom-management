from django.db import models
from users.models import User

class ClockIssue(models.Model):
    """辅导员发布的考勤任务"""
    address = models.CharField(max_length=255, verbose_name='考勤地点')
    location = models.JSONField(verbose_name='经纬度')          # 例如 [120.1, 30.2]
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                  related_name='issued_clocks', verbose_name='发布人')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '考勤任务'
        verbose_name_plural = '考勤任务'

    def __str__(self):
        return f"{self.address} ({self.start_time}~{self.end_time})"


class ClockRecord(models.Model):
    """学生打卡记录"""
    STATUS_CHOICES = (
        ('normal', '正常打卡'),
        ('late', '迟到'),
        ('supplement', '补卡'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='clock_records', verbose_name='学生')
    issue = models.ForeignKey(ClockIssue, on_delete=models.CASCADE,
                              related_name='records', verbose_name='所属考勤')
    clock_time = models.DateTimeField(auto_now_add=True, verbose_name='打卡时间')
    address = models.CharField(max_length=255, verbose_name='打卡地点')
    location = models.JSONField(verbose_name='打卡经纬度')
    status = models.CharField(max_length=20, default='normal', verbose_name='状态')  # normal, late, supplement

    class Meta:
        unique_together = ('student', 'issue')   # 一个学生一次考勤只能打一次
        verbose_name = '打卡记录'
        verbose_name_plural = '打卡记录'

    def __str__(self):
        return f"{self.student} - {self.clock_time}"


class Leave(models.Model):
    """请假申请"""
    TYPE_CHOICES = (
        ('leave', '请假'),
        ('supplement', '补卡'),
    )
    STATUS_CHOICES = (
        ('pending', '待审批'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    )
    LEAVE_TYPE_CHOICES = (
        ('sick', '病假'),
        ('personal', '事假'),
        ('night_out', '夜不归寝事假'),
        ('other', '其他'),
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, blank=True, null=True,
                                  verbose_name='请假类型')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='申请类型')
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='leaves', verbose_name='学生')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    reason = models.TextField(verbose_name='请假原因')
    proof_images = models.JSONField(default=list, blank=True, verbose_name='证明材料')  # 图片路径列表
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    reject_reason = models.TextField(blank=True, verbose_name='拒绝原因')
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='approved_leaves', verbose_name='审批人')
    apply_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '请假记录'
        verbose_name_plural = '请假记录'

    def __str__(self):
        return f"{self.student} 请假 {self.start_time}~{self.end_time}"



class Record(models.Model):
    """备案登记（节假日、寒暑假、实习等）"""
    RECORD_TYPE_CHOICES = (
        ('holiday', '节假日'),
        ('vacation', '寒暑假'),
        ('intern', '实习'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records', verbose_name='学生')
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES, verbose_name='备案类型')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    destination = models.CharField(max_length=255, blank=True, verbose_name='去向/地点')
    emergency_contact = models.CharField(max_length=50, verbose_name='紧急联系人')
    emergency_phone = models.CharField(max_length=20, verbose_name='紧急联系电话')
    # 以下字段为备案人信息（可能是班主任、辅导员、宿舍管理员等，可以存文本或外键）
    # 简单起见，我们存文本，因为备案人可能不是系统用户（如家长），但需求说“备案人（班主任、辅导员、宿舍、紧急联系人）”，可能是指这几类人可以查看？我们先保留文本字段。
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '备案登记'
        verbose_name_plural = '备案登记'

    def __str__(self):
        return f"{self.student} - {self.get_record_type_display()} {self.start_time}~{self.end_time}"

class AutoClockSetting(models.Model):
    """
    辅导员自动考勤设置
    """
    counselor = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='auto_clock_setting',
        limit_choices_to={'role': 'counselor'},  # 只允许辅导员创建
        verbose_name='辅导员'
    )
    is_enabled = models.BooleanField(default=False, verbose_name='是否启用自动发布')
    address = models.CharField(max_length=255, verbose_name='考勤地点')
    location = models.JSONField(verbose_name='经纬度', help_text='格式 [经度, 纬度]')
    start_time = models.TimeField(verbose_name='每日开始时间', help_text='例如 22:00:00')
    end_time = models.TimeField(verbose_name='每日结束时间', help_text='例如 23:59:59')
    # 可选：考勤任务的有效期范围（例如从某天到某天），如果不需要可以不加
    # 我们这里简单处理，只要启用，每天都会创建

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '自动考勤设置'
        verbose_name_plural = '自动考勤设置'

    def __str__(self):
        return f"{self.counselor.username}的自动考勤设置"

class Notification(models.Model):
    SEND_TO_CHOICES = (
        ('all', '全体'),
        ('building', '指定楼栋'),
        ('class', '指定班级'),
        ('user', '指定用户'),
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    send_to = models.CharField(max_length=50, choices=SEND_TO_CHOICES, default='all')
    target_building = models.CharField(max_length=50, blank=True, null=True)
    target_class = models.CharField(max_length=50, blank=True, null=True)
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='target_notifications')
    send_time = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    target_room = models.CharField(max_length=50, blank=True, null=True)
    content_en = models.TextField(blank=True, null=True, verbose_name='英文内容')

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'

    def __str__(self):
        return self.title


class NotificationTemplate(models.Model):
    """通知模板"""
    CATEGORY_CHOICES = (
        ('notice', '公告'),
        ('warning', '预警'),
        ('reminder', '提醒'),
        ('custom', '自定义'),
    )
    name = models.CharField(max_length=100, verbose_name='模板名称')
    content = models.TextField(verbose_name='模板内容')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='custom', verbose_name='分类')
    variables = models.JSONField(default=list, blank=True, verbose_name='变量列表', help_text='例如 ["学生姓名", "寝室号"]')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates', verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '通知模板'
        verbose_name_plural = '通知模板'

    def __str__(self):
        return self.name


class UserNotification(models.Model):
    """用户与通知的关联（记录已读状态、催办状态）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications', verbose_name='用户')
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='user_notifications', verbose_name='通知')
    is_read = models.BooleanField(default=False, verbose_name='是否已读')
    read_time = models.DateTimeField(null=True, blank=True, verbose_name='阅读时间')
    is_urged = models.BooleanField(default=False, verbose_name='是否已催办')
    urged_count = models.IntegerField(default=0, verbose_name='催办次数')
    urged_last_time = models.DateTimeField(null=True, blank=True, verbose_name='最后催办时间')

    class Meta:
        unique_together = ('user', 'notification')  # 一个用户对一个通知只有一条记录
        verbose_name = '用户通知'
        verbose_name_plural = '用户通知'

    def __str__(self):
        return f"{self.user.username} - {self.notification.title}"

class Message(models.Model):
    """用户私信消息"""
    sender = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='发送者'
    )
    receiver = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name='接收者'
    )
    content = models.TextField(verbose_name='消息内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='发送时间')
    is_read = models.BooleanField(default=False, verbose_name='是否已读')

    class Meta:
        ordering = ['created_at']
        verbose_name = '私信'
        verbose_name_plural = '私信'

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.content[:20]}"