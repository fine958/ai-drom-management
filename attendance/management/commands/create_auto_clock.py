from django.core.management.base import BaseCommand
from attendance.cron import create_auto_clock_issues

class Command(BaseCommand):
    help = '自动创建考勤任务'

    def handle(self, *args, **options):
        create_auto_clock_issues()
        self.stdout.write(self.style.SUCCESS('成功创建自动考勤任务'))