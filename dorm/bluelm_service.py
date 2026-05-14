"""
蓝心大模型文本生成服务
用于生成整改报告、卫生周报等文本内容
"""
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BlueLMService:
    """蓝心大模型服务封装（OpenAI 兼容格式）"""

    def __init__(self):
        self.api_url = settings.BLUELM_API_URL
        self.api_key = settings.BLUELM_API_KEY
        self.use_mock = settings.BLUELM_USE_MOCK
        self.model = settings.BLUELM_MODEL

    def generate_report(self, system_prompt, user_prompt):
        """
        调用蓝心大模型生成文本

        参数:
            system_prompt: 系统提示词（设定AI角色和行为规范）
            user_prompt: 用户提示词（具体的任务内容）

        返回:
            str: AI生成的文本内容
        """
        # Mock 模式：直接返回模拟报告，不依赖真实API
        if self.use_mock:
            return self._mock_generate_report()

        # 真实调用蓝心大模型API
        return self._call_bluelm_api(system_prompt, user_prompt)

    def _call_bluelm_api(self, system_prompt, user_prompt):
        """
        调用蓝心大模型 API（OpenAI 兼容格式）
        参考文档: https://deepwiki.com/vivo-ai-lab/BlueLM/3.4-openai-api-integration
        """
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
                "temperature": 0.7,
                "max_tokens": 1000
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                # 标准 OpenAI 格式返回
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"蓝心大模型API调用失败: {response.status_code} - {response.text}")
                return self._get_error_message()

        except Exception as e:
            logger.error(f"蓝心大模型API异常: {str(e)}")
            return self._get_error_message()

    def _mock_generate_report(self):
        """Mock模式：模拟整改报告（用于开发调试）"""
        return """【模拟报告】
总体评价：该宿舍整体卫生状况一般，存在一定改进空间。

主要问题：
1. 地面卫生：地面有纸屑和杂物，未及时清扫
2. 床铺整理：被子未叠放整齐
3. 物品摆放：桌面物品杂乱，未分类收纳

整改建议：
1. 每日安排值日生负责地面清扫和垃圾清理
2. 起床后立即整理床铺，保持被子叠放整齐
3. 个人物品分类收纳，桌面保持整洁有序

整改期限：请在3个工作日内完成整改，届时将进行复查。"""

    def _get_error_message(self):
        """返回错误时的默认提示"""
        return "AI服务暂时不可用，请稍后重试或手动填写整改建议。"


# 创建全局实例，方便导入使用
bluelm_service = BlueLMService()


def generate_report_text(system_prompt, user_prompt):
    """
    对外暴露的便捷函数
    """
    return bluelm_service.generate_report(system_prompt, user_prompt)