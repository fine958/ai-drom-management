# dorm/doubao_text_service.py
"""
豆包文本生成服务（用于周报、整改报告等纯文本任务）
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DoubaoTextService:
    def __init__(self):
        self.api_key = settings.DOUBAO_API_KEY
        self.use_mock = settings.DOUBAO_USE_MOCK
        self.model = settings.DOUBAO_TEXT_MODEL
        self.api_url = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'

    def generate(self, system_prompt, user_prompt):
        """生成文本"""
        if self.use_mock:
            return self._mock_response()

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.7
            }
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60   # 文本生成可以稍长
            )
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"豆包文本API失败: {response.status_code} - {response.text}")
                return self._mock_response()
        except Exception as e:
            logger.error(f"豆包文本API异常: {str(e)}")
            return self._mock_response()

    def _mock_response(self):
        return "【模拟周报】本周宿舍卫生整体良好，平均分75分，B级宿舍占主导。主要问题：地面垃圾和被子未叠，请加强日常管理。"


# 全局单例
text_service = DoubaoTextService()


def generate_weekly_report(system_prompt, user_prompt):
    """便捷函数"""
    return text_service.generate(system_prompt, user_prompt)