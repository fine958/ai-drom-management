from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """自定义用户模型，继承Django自带的AbstractUser，保留用户名密码等基础字段"""
    # 角色选择，用元组表示，第一个是存储值，第二个是显示名称
    ROLE_CHOICES = (
        ('student', '学生'),
        ('teacher', '班主任'),
        ('counselor', '辅导员'),
        ('dorm_admin', '宿管科'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', verbose_name='角色')
    student_id = models.CharField(max_length=20, blank=True, null=True, verbose_name='学号/工号')
    phone_number = models.CharField(max_length=11, blank=True, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')

    # 宿舍信息（学生用）
    dorm_building = models.CharField(max_length=50, blank=True, verbose_name='楼栋')
    dorm_floor = models.CharField(max_length=20, blank=True, verbose_name='楼层')
    dorm_room = models.CharField(max_length=20, blank=True, verbose_name='寝室号')

    # 班级信息（学生/班主任用）
    major = models.CharField(max_length=50, blank=True, verbose_name='专业')
    class_name = models.CharField(max_length=50, blank=True, verbose_name='班级')

    # 管理的班级（班主任/辅导员用，用JSON字段存储多个班级）
    supervise_classes = models.JSONField(default=list, blank=True, verbose_name='管理的班级列表')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"


class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks', verbose_name='提交用户')
    content = models.TextField(verbose_name='反馈内容')          # 原始内容（可能是英文或中文）
    content_zh = models.TextField(blank=True, null=True, verbose_name='中文内容')  # 新增：翻译后的中文
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    is_resolved = models.BooleanField(default=False, verbose_name='是否已处理')
    reply = models.TextField(blank=True, verbose_name='回复内容')
    admin_reply = models.TextField(blank=True, verbose_name='管理员回复')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '反馈'
        verbose_name_plural = '反馈'

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"