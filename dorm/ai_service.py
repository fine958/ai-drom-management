# dorm/ai_service.py
"""
豆包AI图像识别服务
用于识别宿舍照片中的违规行为
"""
import base64
import json
import logging
from django.conf import settings
from openai import OpenAI

# 获取logger
logger = logging.getLogger(__name__)


class DoubaoAIService:
    """豆包AI服务封装"""

    def __init__(self):
        # 从settings读取配置
        self.api_key = getattr(settings, 'DOUBAO_API_KEY', '')
        self.endpoint_id = getattr(settings, 'DOUBAO_ENDPOINT_ID', '')
        self.use_mock = getattr(settings, 'DOUBAO_USE_MOCK', True)
        self.model = getattr(settings, 'DOUBAO_MODEL', 'Doubao-vision-pro-32k')

        # API地址（视觉模型）
        self.api_url = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'

    def analyze_dorm_image(self, image_base64):
        """
        分析宿舍照片，识别违规项

        参数:
            image_base64: 图片的base64编码字符串（不含data:image前缀）

        返回:
            dict: 识别结果，包含violations列表、overall_grade、suggestions
        """
        if self.use_mock:
            return self._mock_analyze()

        # 真实调用豆包API
        return self._call_doubao_api(image_base64)

    def _call_doubao_api(self, image_base64):
        """
        调用豆包视觉模型API
        """
        try:
            import requests

            # 构造提示词
            prompt = """你是一个宿舍卫生检查专家。请分析这张宿舍照片，识别以下违规项：
 要求
一、墙面    1.寝室门贴、挂牌整齐，信息完整，无小广告；
    2.值日表、文明公约等张贴整齐，无脱落、破损，寝室值日制度完善并落实；
二、地面    3.地面整洁，无垃圾杂物；
    4.门内无垃圾堆放；
    5.行李箱摆放整齐有序（靠衣柜放置）
    6.劳动工具统一摆放；
    7.鞋子摆放整齐有序；
三、桌面    8.桌面整洁，学习用品、生活物品摆放整齐有序，无杂物垃圾；
    9.无私拉乱接电线和网线；（包括插线板）
四、床铺    10.床面整洁，平整，床单叠放到位；
    11.被子叠方正，枕头摆放在被子上；
    12.蚊帐、床帷无人时需打开；
    13.衣服允许整齐统一地挂靠在靠墙一侧的床沿上；
    14.床下物品整齐规范，人不在寝室时，椅子上不挂放衣服,背包等物品；
五、卫生间、洗漱台    15.洗漱台整洁（包括镜子），生活用品摆放整齐有序，毛巾挂放统一；
    16.水槽无污垢；
    17.卫生间设施、墙面、地面干净，无垃圾堆放；
六、其他    18.窗门、气窗、墙角无积灰、蛛网；
    19.阳台整洁，洗衣台上生活用品摆放整齐有序，不堆放垃圾杂物；
    20.室内空气清新无异味；
七、出现以下情形之一，直接评为“C”等：    1.违章用电、使用大功率电器；
    2.存放管制刀具、酒瓶等现象；
    3.饲养宠物；
    4.态度不端正；
    5.门外垃圾堆放；
    6.垃圾大量堆放。
A等寝室：检查内容全部符合卫生标准为“A”等；B等寝室：检查内容中有1-2项不合格为“B”等； C等寝室：检查内容中有3项及以上不合格为“C”等。严格遵守扣分规定给出具体等级。

请以JSON格式返回结果，格式如下：
{
    "violations": "详细描述",
    "overall_grade": "A/B/C",
    "suggestions": "整改建议"
}

如果没有发现违规，violations返回空列表[]。"""

            # 构建请求体（按照火山引擎API格式）
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的宿舍卫生检查AI助手。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.3
            }

            # 发送请求
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                # 解析AI返回的JSON
                return self._parse_ai_response(ai_response)
            else:
                logger.error(f"豆包API调用失败: {response.status_code} - {response.text}")
                return self._get_error_result()

        except Exception as e:
            logger.error(f"豆包API异常: {str(e)}")
            return self._get_error_result()

    def _parse_ai_response(self, ai_response):
        """解析AI返回的JSON"""
        try:
            # 尝试提取JSON部分
            if '```json' in ai_response:
                json_str = ai_response.split('```json')[1].split('```')[0].strip()
            elif '```' in ai_response:
                json_str = ai_response.split('```')[1].split('```')[0].strip()
            else:
                json_str = ai_response.strip()

            result = json.loads(json_str)
            # 确保返回格式正确
            return {
                'violations': result.get('violations', ''),
                'overall_grade': result.get('overall_grade', '待评分'),
                'suggestions': result.get('suggestions', '')
            }
        except json.JSONDecodeError:
            logger.error(f"解析AI响应失败: {ai_response}")
            return self._get_error_result()

    def _get_error_result(self):
        """返回错误时的默认结果"""
        return {
            'violations': [],
            'overall_grade': '识别失败',
            'suggestions': 'AI识别失败，请手动填写扣分项'
        }

    def _mock_analyze(self):
        """
        Mock模式：模拟AI识别结果（用于开发调试）
        """
        return {
            "violations": [
                {
                    "item": "地面有垃圾",
                    "severity": "medium",
                    "description": "地面有纸屑和零食包装"
                },
                {
                    "item": "被子未叠",
                    "severity": "low",
                    "description": "被子凌乱未整理"
                }
            ],
            "overall_grade": "合格",
            "suggestions": "请及时打扫地面卫生，整理床铺"
        }


# 创建全局实例
ai_service = DoubaoAIService()


def analyze_dorm_image(image_base64):
    """
    对外暴露的便捷函数
    """
    return ai_service.analyze_dorm_image(image_base64)