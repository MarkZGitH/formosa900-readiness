"""
视觉解析模块 - 把码表截图解析成结构化训练数据
使用OpenRouter的Vision-capable模型 (默认Gemini 2.5 Flash)
"""

import base64
import json
import re
from typing import Dict, Optional
import requests


# OpenRouter API endpoint
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# 视觉提取的prompt - 严格要求JSON输出
VISION_PROMPT = """你是一个自行车码表数据提取专家。从这张码表/骑行APP截图中提取以下字段，
返回严格的JSON对象（不要有任何markdown代码块标记，直接返回JSON）。
无法识别的字段返回null。

提取字段:
{
  "distance_km": 距离公里数,
  "active_duration_min": 活动时长分钟数 (把HH:MM:SS或MM:SS转成分钟),
  "ascent_m": 累计爬升米数,
  "avg_speed_kmh": 平均速度公里每小时,
  "avg_hr": 平均心率 (或null),
  "avg_power_w": 平均功率瓦特 (或null),
  "normalized_power_w": 标准化功率瓦特 (或null),
  "cadence": 平均踏频 (或null),
  "calories": 消耗卡路里 (或null),
  "device_brand_guess": "Garmin|Wahoo|Bryton|Hammerhead|Strava|unknown"
}

重要说明:
1. 如果单位是英里(mi)，转换为公里 (×1.609)
2. 如果单位是英尺(ft)，转换为米 (×0.3048)
3. 数字字段只返回纯数字，不要带单位
4. 必须返回有效的JSON，不要任何额外文字
"""


def image_to_base64(image_bytes: bytes) -> str:
    """把图片二进制数据转成base64字符串"""
    return base64.b64encode(image_bytes).decode('utf-8')


def extract_json(text: str) -> Dict:
    """
    从AI返回的文本中提取JSON对象
    有些模型会用```json包裹，有些不会，要兼容处理
    """
    text = text.strip()

    # 匹配 ```json ... ``` 或 ``` ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # 直接找第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]

    return json.loads(text)


def parse_screenshot(
    image_bytes: bytes,
    api_key: str,
    model: str = "google/gemini-2.5-flash"
) -> Optional[Dict]:
    """
    调用Vision AI解析截图，返回提取的结构化数据
    失败时返回None

    ★ try/except 异常处理 (网络/API/解析错误兜底)
    """
    if not api_key:
        raise ValueError("OpenRouter API key 未配置")

    # 1. 图片转base64并构造data URL
    b64 = image_to_base64(image_bytes)
    image_data_url = f"data:image/jpeg;base64,{b64}"

    # 2. 构造OpenRouter请求
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/formosa900-readiness",
        "X-Title": "Formosa 900 Readiness Coach"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_data_url}}
                ]
            }
        ],
        "temperature": 0.1,  # 低温度确保输出稳定
        "max_tokens": 2000,
        "reasoning": {"effort": "minimal"}
    }

    # 3. 发请求 + 多层异常兜底
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return extract_json(content)

    except requests.exceptions.Timeout:
        print("⚠️ Vision API 超时 (>30秒)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Vision API 请求失败: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"⚠️ Vision API 返回结构异常: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠️ Vision AI 返回的不是有效JSON: {e}")
        return None
