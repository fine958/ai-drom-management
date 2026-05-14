from django.contrib import admin
from .models import DormInspect, PowerInspect, WeeklyReport

# 注册 DormInspect
@admin.register(DormInspect)
class DormInspectAdmin(admin.ModelAdmin):
    list_display = ('id', 'building', 'floor', 'room', 'grade', 'inspect_time', 'inspector')
    list_filter = ('building', 'grade')
    search_fields = ('building', 'floor', 'room')

# 注册 PowerInspect
@admin.register(PowerInspect)
class PowerInspectAdmin(admin.ModelAdmin):
    list_display = ('id', 'building', 'floor', 'room', 'item_name', 'inspect_time')
    list_filter = ('building',)
    search_fields = ('building', 'room', 'item_name')

# 定义 action 函数
def generate_this_week_report(modeladmin, request, queryset):
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    modeladmin.message_user(request, f"已生成 {week_start} 至 {week_end} 周报")
generate_this_week_report.short_description = "生成本周周报"

# 注册 WeeklyReport（只保留一个）
@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'week_end', 'total', 'avg_score', 'grade_a_count', 'grade_b_count', 'grade_c_count', 'created_at')
    list_filter = ('week_start', 'created_at')
    search_fields = ('week_start', 'week_end')
    readonly_fields = ('week_start', 'week_end', 'total', 'avg_score', 'grade_a_count', 'grade_b_count', 'grade_c_count', 'top_violations', 'report_text', 'created_at')
    fieldsets = (
        ('统计信息', {
            'fields': ('week_start', 'week_end', 'total', 'avg_score', 'grade_a_count', 'grade_b_count', 'grade_c_count')
        }),
        ('违规项', {
            'fields': ('top_violations',)
        }),
        ('周报正文', {
            'fields': ('report_text',)
        }),
        ('元信息', {
            'fields': ('created_at',)
        }),
    )
    actions = [generate_this_week_report]   # 加上 action


from django.contrib import admin
from .models import DormWarning

@admin.register(DormWarning)
class DormWarningAdmin(admin.ModelAdmin):
    list_display = ('id', 'building', 'room', 'risk_level', 'trigger_reason', 'created_at', 'is_handled')
    list_filter = ('risk_level', 'is_handled', 'created_at')
    search_fields = ('building', 'room', 'trigger_reason')
    readonly_fields = ('created_at', 'ai_suggestion', 'trigger_reason', 'risk_level')
    fieldsets = (
        (None, {
            'fields': ('building', 'room', 'risk_level', 'trigger_reason')
        }),
        ('AI建议', {
            'fields': ('ai_suggestion',)
        }),
        ('处理状态', {
            'fields': ('is_handled', 'handled_by', 'handled_at')
        }),
        ('元信息', {
            'fields': ('created_at',)
        }),
    )