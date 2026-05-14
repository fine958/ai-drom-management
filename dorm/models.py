from django.db import models
from users.models import User

# dorm/models.py

class DormInspect(models.Model):
    GRADE_CHOICES = (
        ('A', 'A级'),
        ('B', 'B级'),
        ('C', 'C级'),
    )
    building = models.CharField(max_length=50, verbose_name='楼栋')
    floor = models.CharField(max_length=20, verbose_name='楼层')
    room = models.CharField(max_length=20, verbose_name='寝室号')
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES, verbose_name='等级')  # 长度改为1
    regulations = models.JSONField(verbose_name='违反条例')
    images = models.JSONField(verbose_name='图片列表', default=list)
    inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  related_name='inspected_records', verbose_name='检查人')
    inspect_time = models.DateTimeField(auto_now_add=True, verbose_name='检查时间')
    remarks = models.TextField(blank=True, verbose_name='备注')
    class_name = models.CharField(max_length=50, blank=True, verbose_name='班级')

    class Meta:
        ordering = ['-inspect_time']
        verbose_name = '卫生考评'
        verbose_name_plural = '卫生考评'

    def __str__(self):
        return f"{self.building}-{self.floor}-{self.room} {self.get_grade_display()}"


class PowerInspect(models.Model):
    """大功率电器检查记录"""
    building = models.CharField(max_length=50, verbose_name='楼栋')
    floor = models.CharField(max_length=20, verbose_name='楼层')
    room = models.CharField(max_length=20, verbose_name='寝室号')
    item_name = models.CharField(max_length=100, verbose_name='违规物品')
    description = models.TextField(verbose_name='违规说明')
    images = models.JSONField(verbose_name='图片列表')
    class_name = models.CharField(max_length=50, blank=True, verbose_name='班级')
    inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='检查人')
    inspect_time = models.DateTimeField(auto_now_add=True, verbose_name='检查时间')

    class Meta:
        verbose_name = '大功率检查'
        verbose_name_plural = '大功率检查'

    def __str__(self):
        return f"{self.room} - {self.item_name}"


class DormWarning(models.Model):
    RISK_LEVELS = (
        ('high', '高风险'),
        ('medium', '中风险'),
        ('low', '低风险'),
    )
    building = models.CharField(max_length=50, verbose_name='楼栋')
    room = models.CharField(max_length=20, verbose_name='寝室号')
    trigger_reason = models.TextField(verbose_name='触发原因')   # 如“近28天C级2次”
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, verbose_name='风险等级')
    ai_suggestion = models.TextField(verbose_name='AI预警建议')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='预警时间')
    is_handled = models.BooleanField(default=False, verbose_name='是否已处理')
    handled_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_warnings', verbose_name='处理人'
    )
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')

    class Meta:
        verbose_name = '寝室预警'
        verbose_name_plural = '寝室预警'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.building}栋{self.room}室 - {self.get_risk_level_display()}"

class WeeklyReport(models.Model):
    """卫生周报记录"""
    week_start = models.DateField(verbose_name='周起始日期')
    week_end = models.DateField(verbose_name='周结束日期')
    total = models.IntegerField(verbose_name='检查宿舍总数')
    avg_score = models.FloatField(verbose_name='平均分')
    grade_a_count = models.IntegerField(verbose_name='A级宿舍数')
    grade_b_count = models.IntegerField(verbose_name='B级宿舍数')
    grade_c_count = models.IntegerField(verbose_name='C级宿舍数')
    top_violations = models.JSONField(verbose_name='高频违规项', default=list)
    report_text = models.TextField(verbose_name='周报正文')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='生成时间')

    class Meta:
        ordering = ['-week_start']
        verbose_name = '卫生周报'
        verbose_name_plural = '卫生周报'

    def __str__(self):
        return f"{self.week_start} 至 {self.week_end} 周报"


