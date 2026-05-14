from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


class UserAdmin(BaseUserAdmin):
    # 在列表页面显示哪些字段
    list_display = ('id', 'username', 'role', 'student_id', 'dorm_building', 'dorm_room', 'is_staff')
    # 添加过滤选项
    list_filter = ('role', 'is_staff', 'is_superuser')
    # 搜索字段
    search_fields = ('username', 'student_id')
    # 编辑页面字段布局（可按需自定义）
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('role', 'student_id', 'phone_number', 'avatar')}),
        ('宿舍信息', {'fields': ('dorm_building', 'dorm_floor', 'dorm_room')}),
        ('班级信息', {'fields': ('major', 'class_name', 'supervise_classes')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    # 添加用户时的字段（必须包含）
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'student_id'),
        }),
    )


# 注册 User 模型
admin.site.register(User, UserAdmin)




from django.contrib import admin
from .models import Feedback   # 导入 Feedback 模型

class FeedbackAdmin(admin.ModelAdmin):
    # 列表页显示的字段
    list_display = ('id', 'user', 'content_preview', 'created_at', 'is_resolved', 'admin_reply_preview')
    # 右侧过滤器，方便按状态筛选
    list_filter = ('is_resolved', 'created_at')
    # 搜索框，可以搜用户名或内容
    search_fields = ('user__username', 'user__student_id', 'content')
    # 在列表页可以直接编辑的字段（可选）
    list_editable = ('is_resolved',)
    # 默认按创建时间倒序排列
    ordering = ('-created_at',)
    # 只读字段，防止误改
    readonly_fields = ('user', 'content', 'created_at')

    # 自定义显示内容预览（截取前50个字符）
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '反馈内容'

    def admin_reply_preview(self, obj):
        return obj.admin_reply[:50] + '...' if obj.admin_reply and len(obj.admin_reply) > 50 else obj.admin_reply
    admin_reply_preview.short_description = '管理员回复'

# 注册 Feedback 模型到 admin
admin.site.register(Feedback, FeedbackAdmin)