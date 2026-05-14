# dorm/doubao_translation_service.py
"""
豆包AI翻译服务
用于中英文翻译，支持批量处理。
"""

# dorm/doubao_translation_service.py
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def call_translate_api(text_list, target_language="en"):
    """
    使用豆包文本生成模型实现翻译（无需专用翻译模型）
    target_language: "en" (英) 或 "zh" (中)
    """
    if getattr(settings, 'DOUBAO_USE_MOCK', False):
        return {"translated_texts": [f"[Mock] {text}" for text in text_list]}

    api_key = settings.DOUBAO_API_KEY
    # 使用你已有的文本生成模型（确保该模型已开通）
    model = getattr(settings, 'DOUBAO_TEXT_MODEL', 'doubao-1-5-pro-32k-250115')
    api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    translated_texts = []
    for text in text_list:
        # 根据目标语言构造提示词
        if target_language == "en":
            prompt = f"请将以下中文翻译成英文，只输出翻译结果，不要有任何额外解释：\n{text}"
        else:
            prompt = f"请将以下英文翻译成中文，只输出翻译结果，不要有任何额外解释：\n{text}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的翻译助手，只输出翻译结果，不要添加任何额外内容。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                translated = result['choices'][0]['message']['content'].strip()
                translated_texts.append(translated)
            else:
                logger.error(f"翻译失败: {response.status_code} - {response.text}")
                translated_texts.append(text)  # 失败时返回原文
        except Exception as e:
            logger.error(f"翻译异常: {str(e)}")
            translated_texts.append(text)

    return {"translated_texts": translated_texts}