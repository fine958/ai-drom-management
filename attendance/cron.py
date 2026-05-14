from datetime import datetime, time, timedelta
from django.utils import timezone
from .models import AutoClockSetting, ClockIssue

def create_auto_clock_issues():
    """
    自动创建考勤任务：每天运行一次，检查所有启用的设置，为每个设置创建当天的考勤任务
    """
    today = timezone.now().date()
    for setting in AutoClockSetting.objects.filter(is_enabled=True):
        # 构建今天的开始时间和结束时间
        start_datetime = timezone.make_aware(datetime.combine(today, setting.start_time))
        end_datetime = timezone.make_aware(datetime.combine(today, setting.end_time))

        # 如果结束时间小于开始时间，说明跨夜，结束时间应为明天
        if setting.end_time <= setting.start_time:
            end_datetime += timedelta(days=1)

        # 检查是否已经存在相同时间段（避免重复创建）
        if ClockIssue.objects.filter(
            issued_by=setting.counselor,
            start_time=start_datetime,
            end_time=end_datetime
        ).exists():
            continue  # 已存在，跳过

        # 创建考勤任务
        ClockIssue.objects.create(
            address=setting.address,
            location=setting.location,
            start_time=start_datetime,
            end_time=end_datetime,
            issued_by=setting.counselor
        )