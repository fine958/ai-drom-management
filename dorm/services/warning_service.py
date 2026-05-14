"""
宿舍卫生预警服务
根据历史考评数据筛选高危寝室，调用AI生成预警建议
"""
import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from collections import Counter
from dorm.models import DormInspect, DormWarning
from dorm.doubao_text_service import generate_weekly_report  # 复用文本生成


def get_warning_rooms(days=28):
    """
    扫描过去 days 天内的考评记录，返回触发预警的寝室列表
    规则（可自定义）：
    - C 级次数 >= 2 次
    - 或违规项总数（去重） >= 3
    - 或连续两周为 C 级（暂不实现，可后续扩展）
    返回格式: [
        {
            'building': 'A',
            'room': '101',
            'c_count': 2,
            'violations_list': ['地面垃圾', '违规电器'],
            'last_inspect_time': datetime,
        },
        ...
    ]
    """
    start_date = timezone.now().date() - timedelta(days=days)
    inspects = DormInspect.objects.filter(inspect_time__date__gte=start_date)

    # 按寝室分组
    rooms_data = {}
    for inspect in inspects:
        key = (inspect.building, inspect.room)
        if key not in rooms_data:
            rooms_data[key] = {
                'building': inspect.building,
                'room': inspect.room,
                'c_count': 0,
                'all_violations': [],
                'last_time': inspect.inspect_time,
                'grades': []
            }
        # 统计 C 级次数
        if inspect.grade == 'C':
            rooms_data[key]['c_count'] += 1
        # 收集违规项
        reg = inspect.regulations
        if reg:
            if isinstance(reg, str):
                try:
                    reg = json.loads(reg)
                except:
                    reg = []
            rooms_data[key]['all_violations'].extend(reg)
        # 更新最近检查时间
        if inspect.inspect_time > rooms_data[key]['last_time']:
            rooms_data[key]['last_time'] = inspect.inspect_time
        rooms_data[key]['grades'].append(inspect.grade)

    # 筛选触发预警的寝室
    warning_rooms = []
    for key, data in rooms_data.items():
        # 规则1: C级次数 >= 2
        if data['c_count'] >= 2:
            reason = f"近{days}天内出现{data['c_count']}次C级考评"
            risk = 'high' if data['c_count'] >= 3 else 'medium'
            # 去重违规项
            unique_violations = list(set(data['all_violations']))
            warning_rooms.append({
                'building': data['building'],
                'room': data['room'],
                'trigger_reason': reason,
                'risk_level': risk,
                'violations': unique_violations,
                'last_inspect_time': data['last_time'],
                'c_count': data['c_count'],
                'total_inspects': len(data['grades'])
            })

    return warning_rooms


def generate_warning_suggestion(room_info):
    """
    调用 AI 为单个寝室生成预警建议文本
    room_info: 包含 building, room, trigger_reason, violations, c_count 等
    """
    system_prompt = "你是一个严谨、负责的宿舍管理专家，根据寝室的违规记录生成预警提醒。语气要严肃但带有建设性。"
    user_prompt = f"""
寝室：{room_info['building']}栋{room_info['room']}室
触发预警原因：{room_info['trigger_reason']}
历史违规项：{', '.join(room_info['violations']) if room_info['violations'] else '无'}
最近检查时间：{room_info['last_inspect_time'].strftime('%Y-%m-%d')}

请生成一段简短的预警提醒（80字以内），包括：
1. 指出风险（例如“该寝室卫生状况持续下滑”）
2. 给出2条具体整改建议
3. 告知将列为重点检查对象
"""
    # 调用豆包文本生成
    suggestion = generate_weekly_report(system_prompt, user_prompt)
    # 如果生成失败或返回模拟文本，可以加一个默认值
    if not suggestion or "模拟" in suggestion:
        suggestion = f"该寝室近期出现{room_info['c_count']}次C级考评，存在{len(room_info['violations'])}类违规问题。请立即整改，宿舍管理人员将重点复查。"
    return suggestion


def run_warning_scan():
    """
    执行完整预警扫描：获取高危寝室 -> 生成AI建议 -> 存入数据库（去重）
    返回新生成的预警数量
    """
    # 获取所有触发预警的寝室
    warning_rooms = get_warning_rooms(days=28)
    new_count = 0
    for room in warning_rooms:
        # 检查是否已经存在未处理的预警（同一寝室7天内未处理的不重复生成）
        existing = DormWarning.objects.filter(
            building=room['building'],
            room=room['room'],
            is_handled=False,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).exists()
        if existing:
            continue
        # 生成 AI 建议
        ai_text = generate_warning_suggestion(room)
        # 创建预警记录
        DormWarning.objects.create(
            building=room['building'],
            room=room['room'],
            trigger_reason=room['trigger_reason'],
            risk_level=room['risk_level'],
            ai_suggestion=ai_text,
            is_handled=False
        )
        new_count += 1
    return new_count