from rest_framework import viewsets, permissions
from rest_framework.permissions import DjangoModelPermissions
from .models import DormInspect, PowerInspect
from .serializers import DormInspectSerializer, PowerInspectSerializer
from .ai_service import analyze_dorm_image
from .doubao_text_service import generate_weekly_report  # 复用文本生成函数
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator
from .models import DormWarning
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .doubao_translation_service import call_translate_api
import time
from collections import Counter
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DormInspect
import json
import pandas as pd
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .models import DormInspect
import logging
logger = logging.getLogger(__name__)
import threading
from uuid import uuid4

# 简单的内存存储（生产环境请用 Redis 或数据库）
task_store = {}

def background_generate(task_id, file_content, system_prompt, user_prompt):
    # 这里执行实际生成 HTML 的耗时操作
    try:
        html_code = generate_html_report(system_prompt, user_prompt)  # 你的 DeepSeek 调用
        task_store[task_id] = {'status': 'completed', 'html': html_code}
    except Exception as e:
        task_store[task_id] = {'status': 'failed', 'error': str(e)}

class DormInspectViewSet(viewsets.ModelViewSet):
    queryset = DormInspect.objects.all()
    serializer_class = DormInspectSerializer
    permission_classes = [permissions.IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        queryset = DormInspect.objects.all()

        # 根据角色过滤数据
        if user.role == 'student':
            # 学生只能看自己宿舍的卫生记录
            queryset = queryset.filter(
                building=user.dorm_building,
                room=user.dorm_room
            )
        elif user.role == 'teacher':
            # 班主任看自己班级的记录
            # 假设班主任的 class_name 字段存储了管理的班级
            queryset = queryset.filter(class_name=user.class_name)
        elif user.role == 'counselor':
            # 辅导员看自己楼栋的记录
            queryset = queryset.filter(building=user.dorm_building)
        # 宿管科（dorm_admin）可以看到所有，不用过滤

        # 支持额外的查询参数过滤（例如按楼栋、楼层）
        building = self.request.query_params.get('building')
        floor = self.request.query_params.get('floor')
        if building:
            queryset = queryset.filter(building=building)
        if floor:
            queryset = queryset.filter(floor=floor)

        return queryset

    def perform_create(self, serializer):
        # 当创建记录时，自动将当前登录用户设为检查人
        serializer.save(inspector=self.request.user)


class PowerInspectViewSet(viewsets.ModelViewSet):
    queryset = PowerInspect.objects.all()
    serializer_class = PowerInspectSerializer
    permission_classes = [permissions.IsAuthenticated,DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        queryset = PowerInspect.objects.all()

        # 根据角色过滤数据
        if user.role == 'student':
            # 学生只能看自己宿舍的记录
            queryset = queryset.filter(
                building=user.dorm_building,
                room=user.dorm_room
            )
        elif user.role == 'teacher':
            # 班主任看自己班级的记录
            queryset = queryset.filter(class_name=user.class_name)
        elif user.role == 'counselor':
            # 辅导员看自己楼栋的记录
            queryset = queryset.filter(building=user.dorm_building)
        # 宿管科（dorm_admin）可以看到所有，不用过滤

        # 支持额外的查询参数过滤（例如按楼栋、楼层）
        building = self.request.query_params.get('building')
        floor = self.request.query_params.get('floor')
        if building:
            queryset = queryset.filter(building=building)
        if floor:
            queryset = queryset.filter(floor=floor)

        return queryset

    def perform_create(self, serializer):
        serializer.save(inspector=self.request.user)



# dorm/views.py

class ExportDormInspectView(APIView):
    """
    导出宿舍卫生检查记录为 Excel 文件
    支持筛选条件：
    - building: 楼栋
    - class_name: 班级
    - time_range: week / month / semester（优先级高于 start_date/end_date）
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    权限：辅导员/班主任/宿管科可导出（只能导出自己权限范围内的数据）
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. 权限检查
        if user.role not in ['counselor', 'teacher', 'dorm_admin']:
            return Response(
                {'detail': '您没有权限导出数据'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. 基础查询集
        queryset = DormInspect.objects.all()

        # 3. 根据角色自动限制数据范围
        if user.role == 'counselor':
            if not user.dorm_building:
                return Response(
                    {'detail': '您的账号未关联楼栋，无法导出'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = queryset.filter(building=user.dorm_building)
        elif user.role == 'teacher':
            if not user.class_name:
                return Response(
                    {'detail': '您的账号未关联班级，无法导出'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = queryset.filter(class_name=user.class_name)
        # dorm_admin 无额外过滤

        # 4. 额外筛选参数
        building = request.query_params.get('building')
        if building:
            queryset = queryset.filter(building=building)

        class_name = request.query_params.get('class_name')
        if class_name:
            queryset = queryset.filter(class_name=class_name)

        # 5. 时间筛选（优先级: time_range > start_date/end_date）
        time_range = request.query_params.get('time_range')
        today = timezone.now().date()

        if time_range == 'week':
            # 本周（周一至周日）
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_date = start_of_week
            end_date = end_of_week
        elif time_range == 'month':
            # 本月（1号至月末）
            start_of_month = today.replace(day=1)
            # 下个月的第一天减一天
            if start_of_month.month == 12:
                next_month = start_of_month.replace(year=start_of_month.year+1, month=1)
            else:
                next_month = start_of_month.replace(month=start_of_month.month+1)
            end_of_month = next_month - timedelta(days=1)
            start_date = start_of_month
            end_date = end_of_month
        elif time_range == 'semester':
            # 简化逻辑：上学期（2月-7月）或下学期（9月-1月）
            # 根据当前月份判断所属学期
            month = today.month
            if 2 <= month <= 7:
                start_date = datetime(today.year, 2, 1).date()
                end_date = datetime(today.year, 7, 31).date()
            else:
                # 8月-次年1月视为下学期
                start_date = datetime(today.year, 9, 1).date()
                end_date = datetime(today.year+1, 1, 31).date()
        else:
            # 使用自定义日期，如果没有自定义则不限
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')
            start_date = start_date_str if start_date_str else None
            end_date = end_date_str if end_date_str else None

        # 应用时间范围过滤
        if start_date:
            # 将日期转换为 datetime 范围（当天 00:00:00 到 23:59:59）
            start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            queryset = queryset.filter(inspect_time__gte=start_datetime)
        if end_date:
            end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
            queryset = queryset.filter(inspect_time__lte=end_datetime)

        # 6. 如果没有数据
        if not queryset.exists():
            return Response(
                {'detail': '没有符合条件的数据'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 7. 转换为 DataFrame 并生成 Excel（代码略，与之前相同）
        data = []
        for record in queryset:
            if record.regulations:
                if isinstance(record.regulations, list):
                    regulations_str = ', '.join(record.regulations)
                else:
                    regulations_str = str(record.regulations)
            else:
                regulations_str = ''
            images_str = ', '.join(record.images) if record.images else ''
            local_time = timezone.localtime(record.inspect_time)
            time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')

            data.append({
                'ID': record.id,
                '楼栋': record.building,
                '楼层': record.floor,
                '寝室号': record.room,
                '班级': record.class_name,
                '等级': record.grade,
                '违反条例': regulations_str,
                '图片': images_str,
                '检查人': record.inspector.username if record.inspector else '',
                '检查时间': time_str,
                '备注': record.remarks,
            })

        df = pd.DataFrame(data)
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="dorm_inspect.xlsx"'
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='宿舍卫生检查')

        return response



class AIDetectView(APIView):
    """
    AI识别宿舍照片接口
    POST /api/dorm/ai-detect/
    请求体: {"image": "base64编码的图片"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # 1. 权限检查：只有宿管或辅导员可以调用AI识别
        user = request.user
        if user.role not in ['dorm_admin', 'counselor']:
            return Response(
                {'detail': '您没有权限使用AI识别功能'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. 获取图片数据
        image_base64 = request.data.get('image')
        if not image_base64:
            return Response(
                {'detail': '请提供图片数据'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. 调用AI服务
        result = analyze_dorm_image(image_base64)

        return Response(result, status=status.HTTP_200_OK)


# ========== AI整改报告生成（阶段1）==========
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import DormInspect
from .bluelm_service import generate_report_text
from attendance.models import Notification, UserNotification
from users.models import User


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate_report(request):
    """
    生成宿舍整改报告（使用vivo提供的豆包模型）

    请求体格式：
    方式1 - 通过考评记录ID：
    {
        "inspect_id": 123
    }

    方式2 - 直接传入数据：
    {
        "building": "A",
        "floor": "3",
        "room": "101",
        "grade": 75,
        "violations": ["地面有垃圾", "被子未叠"],
        "remarks": "其他备注信息"
    }
    """
    data = request.data
    inspect_id = data.get('inspect_id')

    # 获取宿舍考评信息
    if inspect_id:
        try:
            inspect = DormInspect.objects.get(id=inspect_id)
            dorm_info = {
                'building': inspect.building,
                'floor': inspect.floor,
                'room': inspect.room,
                'grade': inspect.grade,
                'remarks': inspect.remarks or '',
                'violations': inspect.regulations if inspect.regulations else [],
            }
        except DormInspect.DoesNotExist:
            return Response(
                {'error': '考评记录不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # 直接从请求数据获取
        dorm_info = {
            'building': data.get('building', '未知'),
            'floor': data.get('floor', ''),
            'room': data.get('room', '未知'),
            'grade': data.get('grade', 0),
            'remarks': data.get('remarks', ''),
            'violations': data.get('violations', []),
        }

    # 构造系统提示词（设定AI的角色）
    system_prompt = """你是一个高校宿舍管理助手，专门负责根据宿舍检查结果生成客观、具体、有建设性的整改报告。你的语气要专业、友好，报告内容要清晰、可执行。"""

    # 构造用户提示词（具体的检查数据）
    user_prompt = f"""
    请根据以下宿舍检查数据，生成一份整改报告：

    宿舍信息：{dorm_info['building']}栋{dorm_info['floor']}层{dorm_info['room']}室
    考评得分：{dorm_info['grade']}分
    违规项：{json.dumps(dorm_info['violations'], ensure_ascii=False)}
    备注：{dorm_info['remarks']}

    要求：
    - 直接输出内容，不要输出任何标题。
    - 按以下格式输出：
    1. 总体评价（一句话总结宿舍当前状况）
    若寝室整体没有问题且违规项为空，则只输出这一条，不输出后面的 2、3、4。
    2. 主要问题（列出存在的具体问题）
    3. 整改建议（给出可操作的具体建议）
    4. 整改期限（建议3天内完成）
    """

    # 调用蓝心大模型生成报告
    report_text = generate_report_text(system_prompt, user_prompt)

    building = dorm_info.get('building')
    room = dorm_info.get('room')
    # ========== 新增：翻译整改报告为英文 ==========
    report_en = ''
    if report_text:
        # 如果处于 Mock 模式，可以生成模拟英文或跳过翻译
        if getattr(settings, 'DOUBAO_USE_MOCK', False):
            report_en = f"[Mock English] {report_text[:100]}..."
        else:
            result = call_translate_api([report_text], target_language='en')
            if result.get('translated_texts'):
                report_en = result['translated_texts'][0]
            else:
                # 翻译失败时记录日志（可选）
                import logging
                logging.getLogger(__name__).warning("整改报告翻译失败，英文内容为空")

    # ========== 推送给该寝室的所有学生 ==========
    if building and room:
        students = User.objects.filter(dorm_building=building, dorm_room=room)
        if students.exists():
            # 创建通知记录，同时存入中英文内容
            notification = Notification.objects.create(
                title=f"{building}栋{room}室 卫生检查通知",
                content=report_text,  # 中文原文
                content_en=report_en,  # 英文翻译（可能为空）
                send_to='room',
                target_building=building,
                target_room=room,
                created_by=request.user
            )
            # 批量创建 UserNotification 关联
            user_notification_list = [
                UserNotification(
                    user=student,
                    notification=notification,
                    is_read=False,
                    urged_count=0
                )
                for student in students
            ]
            UserNotification.objects.bulk_create(user_notification_list)

    return Response({
        'report': report_text,
        'dorm_info': dorm_info,
        'status': 'success'
    })

# dorm/views.py 末尾添加

# 等级 -> 分数映射（用于平均分）


GRADE_TO_SCORE = {
    'A': 90,
    'B': 75,
    'C': 60,
}

from .models import WeeklyReport
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_weekly_report(request):
    """
    生成卫生周报（使用豆包文本模型）
    请求体: {"week_start": "2025-04-01"}  # 可选，默认为本周一
    """
    # 1. 确定统计周期（本周一 ~ 周日）
    week_start_str = request.data.get('week_start')
    if week_start_str:
        week_start = timezone.datetime.strptime(week_start_str, '%Y-%m-%d').date()
    else:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # 2. 查询该周考评记录
    inspects = DormInspect.objects.filter(
        inspect_time__date__gte=week_start,
        inspect_time__date__lte=week_end
    )
    total = inspects.count()
    if total == 0:
        return Response({
            'report': f'在 {week_start} 至 {week_end} 期间没有考评记录。',
            'statistics': {
                'week_start': week_start,
                'week_end': week_end,
                'total': 0,
                'avg_score': None,
                'grade_a_count': 0,
                'grade_b_count': 0,
                'grade_c_count': 0,
                'top_violations': [],
            },
            'status': 'success'
        })

    # 3. 统计各等级数量
    grade_a_count = inspects.filter(grade='A').count()
    grade_b_count = inspects.filter(grade='B').count()
    grade_c_count = inspects.filter(grade='C').count()

    # 计算平均分（等级映射分数）
    scores = [GRADE_TO_SCORE[inspect.grade] for inspect in inspects]
    avg_score = sum(scores) / len(scores)

    # 统计高频违规项（前3）
    all_violations = []
    for inspect in inspects:
        reg = inspect.regulations
        if reg:
            # 如果已经是列表，直接使用
            if isinstance(reg, list):
                violations = reg
            # 如果是字符串，尝试解析 JSON
            elif isinstance(reg, str):
                reg_stripped = reg.strip()
                if reg_stripped:  # 非空字符串
                    try:
                        violations = json.loads(reg_stripped)
                    except json.JSONDecodeError:
                        # 解析失败，记录日志并当作空列表
                        logger.warning(f"Invalid regulations JSON: {reg}")
                        violations = []
                else:
                    violations = []
            else:
                violations = []
            all_violations.extend(violations)
    violation_counter = Counter(all_violations)
    top_violations = violation_counter.most_common(3)

    # 4. 构造 AI 提示词
    system_prompt = "你是一个高校宿舍管理助手，根据一周宿舍检查数据生成卫生周报。"

    top_violations_text = "\n".join([f"- {item}: {count}次" for item, count in top_violations]) if top_violations else "无"

    user_prompt = f"""
统计周期：{week_start} 至 {week_end}
检查宿舍总数：{total}
平均分（A=90,B=75,C=60折算）：{avg_score:.1f}
A级宿舍数：{grade_a_count}
B级宿舍数：{grade_b_count}
C级宿舍数：{grade_c_count}
高频违规项（前3）：
{top_violations_text}

请生成卫生周报，内容包括：
1. 整体情况评价（突出A/B/C分布）
2. 主要优点（可表扬A级宿舍多的方面）
3. 突出问题（结合高频违规项分析C级宿舍原因）
4. 下周工作重点（针对C级宿舍和违规项提出改进计划）
"""

    # 5. 调用豆包文本模型生成周报
    report_text = generate_weekly_report(system_prompt, user_prompt)
    try:
        WeeklyReport.objects.create(
            week_start=week_start,
            week_end=week_end,
            total=total,
            avg_score=round(avg_score, 1),
            grade_a_count=grade_a_count,
            grade_b_count=grade_b_count,
            grade_c_count=grade_c_count,
            top_violations=top_violations,
            report_text=report_text,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"保存周报失败: {e}")

        # 返回 Response
    # 6. 返回结果
    return Response({
        'report': report_text,
        'statistics': {
            'week_start': week_start,
            'week_end': week_end,
            'total': total,
            'avg_score': round(avg_score, 1),
            'grade_a_count': grade_a_count,
            'grade_b_count': grade_b_count,
            'grade_c_count': grade_c_count,
            'top_violations': top_violations,
        },
        'status': 'success'
    })


# dorm/views.py 末尾添加

import os
from django.conf import settings

def load_knowledge_base():
    file_path = os.path.join(settings.BASE_DIR, 'dorm', '宿舍管理细则.txt')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""  # 文件不存在则返回空

# 本地知识库（关键词 -> 答案）
LOCAL_QA = {
    "熄灯": "周日至周四晚上23:00熄灯，周五周六23:30熄灯。",
    "大功率": "严禁使用电煮锅、电热毯、电暖器、电炉等违规电器，一经发现没收并通报批评。",
    "外来人员": "禁止留宿外来人员，访客需在22:00前离开。",
    "报修": "关注学校后勤公众号→智慧报修→填写信息，或拨打报修电话12345678。",
    "晚归": "23:30后回宿舍需登记晚归原因，累计3次通报辅导员。",
    "空调": "夏季6月-9月、冬季12月-2月可开空调，温度设置不低于26℃（夏）不高于20℃（冬）。",
    "宠物": "宿舍内禁止饲养猫、狗、仓鼠等宠物。",
    "吸烟": "宿舍楼内全面禁烟，违者通报批评。",
    "违规电器": "电煮锅、热得快、电热毯、电暖器、电炉等均属违规电器，严禁使用。",
    "分数等级": "A级（90分及以上）、B级（60-89分）、C级（60分以下）。",
    "整改": "收到整改通知后需在3天内完成整改，否则将通报辅导员。",
}


def match_local_qa(question):
    """简单关键词匹配，返回答案或None"""
    q_lower = question.lower()
    for keyword, answer in LOCAL_QA.items():
        if keyword in q_lower:
            return answer
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_qa(request):
    """
    智能问答：学生/老师提问宿舍规则相关问题
    请求体: {"question": "寝室可以用电煮锅吗？"}
    """
    question = request.data.get('question', '').strip()
    if not question:
        return Response(
            {'error': '问题不能为空'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. 先尝试本地匹配
    local_answer = match_local_qa(question)
    if local_answer:
        return Response({
            'answer': local_answer,
            'source': 'local'
        })

    # 2. 本地匹配不到，调用豆包AI
    # 构造系统提示词，要求AI基于校园规定回答
    system_prompt = "你是一个高校宿舍管理助手，只能根据以下校园规定回答问题。如果问题超出规定范围，请礼貌回答'根据现有规定，无法找到准确答案，建议咨询辅导员。'"

    knowledge_text = load_knowledge_base()
    user_prompt = f"""
    以下是校园宿舍管理规定：
    {knowledge_text}

    学生提问：{question}

    请根据上述规定给出简洁、友好的回答。如果规定中没有明确答案，请说：“根据现有规定，无法找到准确答案，建议咨询辅导员。”
    """

    # 调用豆包文本生成服务
    answer = generate_weekly_report(system_prompt, user_prompt)

    return Response({
        'answer': answer,
        'source': 'ai'
    })



# 导入预警服务
from .services.warning_service import run_warning_scan
from .models import DormWarning

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_warning_scan(request):
    """手动触发预警扫描（仅限管理员/宿管）"""
    user = request.user
    if user.role not in ['dorm_admin', 'counselor']:
        return Response({'detail': '无权限'}, status=403)
    try:
        count = run_warning_scan()
        return Response({'message': f'扫描完成，新增{count}条预警', 'new_count': count})
    except Exception as e:
        return Response({'error': str(e)}, status=500)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warning_list(request):
    user = request.user
    # 权限判断：学生只能看自己寝室的预警；辅导员/宿管可看所有
    queryset = DormWarning.objects.all()

    if user.role == 'student':
        # 学生只能看到自己寝室的预警
        building = user.dorm_building
        room = user.dorm_room
        if not building or not room:
            return Response({'results': [], 'count': 0, 'message': '您尚未分配寝室'})
        queryset = queryset.filter(building=building, room=room)
    elif user.role in ['counselor', 'dorm_admin']:
        # 辅导员和宿管可以查看所有，不做额外过滤
        pass
    else:
        # 其他角色（如班主任）无权限
        return Response({'detail': '无权限查看'}, status=403)

    # 可选过滤参数
    is_handled = request.query_params.get('is_handled')
    if is_handled is not None:
        if is_handled.lower() == 'true':
            queryset = queryset.filter(is_handled=True)
        elif is_handled.lower() == 'false':
            queryset = queryset.filter(is_handled=False)

    # 排序
    queryset = queryset.order_by('-created_at')

    # 分页
    page = request.query_params.get('page', 1)
    page_size = request.query_params.get('page_size', 20)
    paginator = Paginator(queryset, page_size)
    try:
        current_page = paginator.page(page)
    except:
        current_page = paginator.page(1)

    data = []
    for w in current_page:
        data.append({
            'id': w.id,
            'building': w.building,
            'room': w.room,
            'trigger_reason': w.trigger_reason,
            'risk_level': w.risk_level,
            'risk_level_display': w.get_risk_level_display(),
            'ai_suggestion': w.ai_suggestion,
            'created_at': w.created_at,
            'is_handled': w.is_handled,
            'handled_by': w.handled_by.username if w.handled_by else None,
            'handled_at': w.handled_at,
        })

    return Response({
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': current_page.number,
        'results': data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_warning_handled(request, warning_id):
    """标记预警为已处理（仅限辅导员或宿管）"""
    user = request.user
    if user.role not in ['dorm_admin', 'counselor']:
        return Response({'detail': '无权限'}, status=403)
    try:
        warning = DormWarning.objects.get(id=warning_id)
    except DormWarning.DoesNotExist:
        return Response({'detail': '预警不存在'}, status=404)
    if warning.is_handled:
        return Response({'detail': '该预警已处理'}, status=400)
    warning.is_handled = True
    warning.handled_by = user
    warning.handled_at = timezone.now()
    warning.save()
    return Response({'message': '已标记为处理'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warning_detail(request, warning_id):
    user = request.user
    try:
        warning = DormWarning.objects.get(id=warning_id)
    except DormWarning.DoesNotExist:
        return Response({'detail': '预警不存在'}, status=404)

    # 权限：学生只能看自己寝室的
    if user.role == 'student':
        if warning.building != user.dorm_building or warning.room != user.dorm_room:
            return Response({'detail': '无权限查看'}, status=403)
    elif user.role not in ['counselor', 'dorm_admin']:
        return Response({'detail': '无权限查看'}, status=403)

    data = {
        'id': warning.id,
        'building': warning.building,
        'room': warning.room,
        'trigger_reason': warning.trigger_reason,
        'risk_level': warning.risk_level,
        'risk_level_display': warning.get_risk_level_display(),
        'ai_suggestion': warning.ai_suggestion,
        'created_at': warning.created_at,
        'is_handled': warning.is_handled,
        'handled_by': warning.handled_by.username if warning.handled_by else None,
        'handled_at': warning.handled_at,
    }
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_translate(request):
    """
    通用翻译接口
    请求体: {
        "text": "要翻译的文本",          # 要翻译的文本，支持字符串
        "target_language": "en"        # 目标语言代码，"en"或"zh"
    }
    """
    # 1. 获取请求数据
    text = request.data.get('text')
    target_language = request.data.get('target_language', 'en')

    # 2. 参数校验
    if not text:
        return Response(
            {'error': '请提供要翻译的文本'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3. 调用翻译服务 (将单个文本放入列表中)
    result = call_translate_api([text], target_language)

    # 4. 返回翻译结果
    if result.get('translated_texts'):
        return Response({
            'original_text': text,
            'translated_text': result['translated_texts'][0],
            'target_language': target_language
        })
    else:
        return Response(
            {'error': '翻译失败，请稍后再试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



import pandas as pd
import json
import re
import threading
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .vivo_deepseek_service import generate_html_report
from .task_manager import create_task, update_task, get_task
from collections import Counter

def background_generate(task_id, file_bytes):
    """后台线程：解析Excel并调用DeepSeek生成包含柱状图、折线图、饼图的高级HTML报告"""
    try:
        # 读取Excel
        df = pd.read_excel(file_bytes, engine='openpyxl')
        if df.empty:
            update_task(task_id, "failed", error="Excel无数据")
            return

        # ========== 1. 列名适应（根据您的实际表格修改） ==========
        # 等级列
        grade_col = None
        for col in ['等级', 'grade', '评级']:
            if col in df.columns:
                grade_col = col
                break
        if not grade_col:
            update_task(task_id, "failed", error="Excel缺少等级列（等级/grade/评级）")
            return

        # 违规项列
        violation_col = None
        for col in ['违反的条例', '违反条例','违规项', 'regulations', '问题']:
            if col in df.columns:
                violation_col = col
                break
        if not violation_col:
            # 没有违规列，TOP榜为空，但继续生成其他图表
            print("警告：Excel中没有违规项列，TOP榜将为空")

        # 楼栋列（用于楼栋合格率折线图）
        building_col = None
        for col in ['楼栋', 'building']:
            if col in df.columns:
                building_col = col
                break

        # 房间号列（可选）
        room_col = None
        for col in ['房间号', 'room', '寝室号']:
            if col in df.columns:
                room_col = col
                break

        # 检查时间列（如果有，可用于趋势折线图，这里简单处理）
        # 如果没有时间列，就按楼栋做合格率折线图

        # ========== 2. 统计基础指标 ==========
        total = len(df)

        # 等级分布（A/B/C 或 优秀/良好/合格/不合格）
        grade_counts = df[grade_col].value_counts().to_dict()
        # 标准化映射
        a_keywords = ['A', '优秀']
        b_keywords = ['B', '良好']
        c_keywords = ['C', '合格', '不合格']
        a_count = sum(grade_counts.get(k, 0) for k in a_keywords if k in grade_counts)
        b_count = sum(grade_counts.get(k, 0) for k in b_keywords if k in grade_counts)
        c_count = sum(grade_counts.get(k, 0) for k in c_keywords if k in grade_counts)

        qualified_rate = round((a_count + b_count) / total * 100, 1) if total else 0
        unqualified_rate = round(c_count / total * 100, 1) if total else 0

        # ========== 3. 违规项TOP榜（务必正确提取） ==========
        top_violations = []
        if violation_col:
            all_violations = []
            for val in df[violation_col].dropna():
                if isinstance(val, str):
                    # 如果存储为JSON数组字符串
                    if val.startswith('[') and val.endswith(']'):
                        try:
                            items = json.loads(val)
                            all_violations.extend(items)
                        except:
                            all_violations.append(val)
                    # 如果存储为逗号分隔
                    elif ',' in val:
                        all_violations.extend([v.strip() for v in val.split(',')])
                    else:
                        all_violations.append(val)
                else:
                    all_violations.append(str(val))
            if all_violations:
                counter = Counter(all_violations)
                top_violations = counter.most_common(5)   # [(问题, 次数), ...]
        # 确保即使没有违规数据也显示“暂无”
        if not top_violations:
            top_violations = [['无违规记录', 0]]

        # 违规率（平均每条记录含违规项数）
        total_violations = sum(cnt for _, cnt in top_violations)
        violation_rate = round(total_violations / total, 2) if total else 0

        # ========== 4. 按楼栋统计合格率（用于折线图） ==========
        building_rates = []
        if building_col:
            for building, group in df.groupby(building_col):
                g_counts = group[grade_col].value_counts()
                a_g = sum(g_counts.get(k, 0) for k in a_keywords if k in g_counts)
                b_g = sum(g_counts.get(k, 0) for k in b_keywords if k in g_counts)
                total_g = len(group)
                rate = round((a_g + b_g) / total_g * 100, 1) if total_g else 0
                building_rates.append({'楼栋': building, '合格率': rate})
            building_rates.sort(key=lambda x: x['合格率'], reverse=True)
        else:
            # 如果没有楼栋列，则生成示例数据（避免折线图无数据）
            building_rates = [{'楼栋': '示例', '合格率': qualified_rate}]

        # ========== 5. 寝室红黑榜（如果有房间号） ==========
        red_top = []
        black_top = []
        if building_col and room_col:
            grouped = df.groupby([building_col, room_col])
            dorm_list = []
            for (building, room), group in grouped:
                g_counts = group[grade_col].value_counts()
                a_g = sum(g_counts.get(k, 0) for k in a_keywords if k in g_counts)
                b_g = sum(g_counts.get(k, 0) for k in b_keywords if k in g_counts)
                total_g = len(group)
                rate = round((a_g + b_g) / total_g * 100, 2) if total_g else 0
                dorm_list.append({
                    '寝室': f"{building}栋{room}室",
                    '合格率': rate,
                    '等级': '红榜' if rate >= 80 else '黑榜' if rate < 60 else '正常'
                })
            dorm_list.sort(key=lambda x: x['合格率'], reverse=True)
            red_top = [d for d in dorm_list if d['等级'] == '红榜'][:5]
            black_top = [d for d in dorm_list if d['等级'] == '黑榜'][:5]

        # ========== 6. 构造向AI发送的统计JSON（强制AI使用真实数据） ==========
        stats_for_ai = {
            "总检查寝室数": total,
            "合格率": qualified_rate,
            "不合格率": unqualified_rate,
            "违规率": violation_rate,
            "等级分布": {
                "A级": a_count,
                "B级": b_count,
                "C级": c_count
            },
            "违规问题TOP榜": [{"问题": v, "次数": c} for v, c in top_violations if c > 0],
            "楼栋合格率(用于折线图)": building_rates,
            "红榜寝室": red_top,
            "黑榜寝室": black_top
        }

        # ========== 7. 精心设计的系统提示词（强制AI生成包含指定图表的HTML） ==========
        system_prompt = """你是一个顶级的数据可视化与前端开发专家。你必须根据下方提供的统计数据，生成一个**现代化、高级感、简洁**的HTML仪表盘页面。

要求：
- 使用 Bootstrap 5 和 Chart.js 库。
- 页面布局：顶部为关键指标卡片（总检查数、合格率、不合格率、违规率），中间左侧为**饼图**（展示A/B/C级分布），中间右侧为**柱状图**（展示违规问题TOP榜），下方为**折线图**（展示各楼栋合格率），再下方为红黑榜表格（两个表格分别展示红榜和黑榜的寝室信息）。
- **所有图表的数据必须严格使用下面JSON中提供的真实数值**，绝对不能自己编造。
- 饼图数据：等级分布（A级、B级、C级）。
- 柱状图数据：违规问题TOP榜中的“问题”和“次数”。
- 折线图数据：楼栋合格率中的“楼栋”和“合格率”。
- 红黑榜表格：显示“寝室号”和“合格率(%)”。
- 整体色调：浅灰色背景，卡片有阴影圆角，字体清晰，图表颜色鲜艳但稳重（如蓝绿橙紫）。
- 生成的HTML必须是完整的，包含所有图表和表格，且可直接在浏览器中运行。
- 输出格式：只输出HTML代码，不要用markdown包裹，不要有任何额外解释。"""

        user_prompt = f"""
请根据以下真实统计数据生成HTML报告：

```json
{json.dumps(stats_for_ai, ensure_ascii=False, indent=2)}
"""

        # 调用DeepSeek生成HTML
        html_code = generate_html_report(system_prompt, user_prompt)

        # 提取HTML（兼容多种情况）
        match = re.search(r'<!DOCTYPE html>.*?</html>', html_code, re.DOTALL | re.IGNORECASE)
        if not match:
            match = re.search(r'```html(.*?)```', html_code, re.DOTALL)
            if match:
                html_code = match.group(1).strip()
            else:
                html_code = f"<html><body><pre>{html_code}</pre></body></html>"

        update_task(task_id, "completed", html=html_code)

    except Exception as e:
        update_task(task_id, "failed", error=str(e))

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_generate_report(request):
    """上传Excel，立即返回任务ID"""
    excel_file = request.FILES.get('file')
    if not excel_file:
        return JsonResponse({'error': '请上传Excel文件'}, status=400)

    file_bytes = excel_file.read()
    task_id = create_task()

    # 启动后台线程
    thread = threading.Thread(target=background_generate, args=(task_id, file_bytes))
    thread.daemon = True
    thread.start()

    return JsonResponse({'task_id': task_id, 'status': 'processing'})

@api_view(['GET'])
@permission_classes([])
def get_report_result(request, task_id):
    task = get_task(task_id)
    if not task:
        return JsonResponse({'error': '任务不存在'}, status=404)
    if task['status'] == 'completed':
        return HttpResponse(task['html'], content_type='text/html')
    elif task['status'] == 'failed':
        return JsonResponse({'error': task['error']}, status=500)
    else:
        return JsonResponse({'status': 'processing'})


