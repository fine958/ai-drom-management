# dorm/report_utils.py
from django.utils import timezone
from datetime import timedelta
from collections import Counter
from .models import DormInspect, WeeklyReport
from .doubao_text_service import generate_weekly_report

GRADE_TO_SCORE = {'A': 90, 'B': 75, 'C': 60}
GRADE_MAPPING = {'优秀':'A', '良好':'B', '合格':'C', '不合格':'C', 'A':'A', 'B':'B', 'C':'C'}

def generate_and_save_weekly_report(week_start=None):
    if week_start is None:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    inspects = DormInspect.objects.filter(inspect_time__date__gte=week_start, inspect_time__date__lte=week_end)
    total = inspects.count()
    if total == 0:
        return None, None
    # 统计等级
    normalized_grades = [GRADE_MAPPING.get(i.grade, 'C') for i in inspects]
    grade_a_count = normalized_grades.count('A')
    grade_b_count = normalized_grades.count('B')
    grade_c_count = normalized_grades.count('C')
    scores = [GRADE_TO_SCORE[g] for g in normalized_grades]
    avg_score = sum(scores)/len(scores)
    # 违规项
    all_violations = []
    for i in inspects:
        reg = i.regulations
        if reg:
            if isinstance(reg, str):
                import json
                try:
                    reg = json.loads(reg)
                except:
                    reg = []
            all_violations.extend(reg)
    top_violations = Counter(all_violations).most_common(3)
    # AI 生成报告
    system_prompt = "你是一个高校宿舍管理助手..."
    user_prompt = f"统计周期：{week_start} 至 {week_end}\n..."
    report_text = generate_weekly_report(system_prompt, user_prompt)
    # 保存
    report = WeeklyReport.objects.create(
        week_start=week_start, week_end=week_end,
        total=total, avg_score=round(avg_score,1),
        grade_a_count=grade_a_count, grade_b_count=grade_b_count, grade_c_count=grade_c_count,
        top_violations=top_violations, report_text=report_text
    )
    return report, report_text