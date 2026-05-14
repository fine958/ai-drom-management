import requests
import uuid
from django.conf import settings

def generate_html_report(system_prompt, user_prompt):
    api_url = "https://api-ai.vivo.com.cn/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.VIVO_DEEPSEEK_API_KEY}"
    }
    payload = {
        "requestId": str(uuid.uuid4()),
        "model": "Volc-DeepSeek-V3.2",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "max_tokens": 8192,
        "temperature": 0.7
    }
    response = requests.post(api_url, json=payload, headers=headers, timeout=360)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"<h1>API错误</h1><p>{response.text}</p>"