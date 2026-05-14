from django.core.management.base import BaseCommand
from dorm.services.warning_service import run_warning_scan

class Command(BaseCommand):
    help = '扫描宿舍考评记录，生成预警'

    def handle(self, *args, **options):
        count = run_warning_scan()
        self.stdout.write(self.style.SUCCESS(f'预警扫描完成，新增 {count} 条预警'))