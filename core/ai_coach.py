"""
AI 教练模块 - 分析单次训练 + 给出下一步建议

v3: 加入第6维度"有氧基础"的解读
"""

import json
from typing import Dict, List, Optional
import requests

from core.vision_parser import OPENROUTER_URL, extract_json


# 维度key到中文名的映射 (供UI和prompt使用)
DIMENSION_NAMES_CN = {
    "volume": "周均训练量",
    "endurance": "单次耐力",
    "climbing": "爬升能力",
    "consistency": "训练一致性",
    "recovery": "恢复/背靠背能力",
    "aerobic_base": "有氧基础"
}


def build_coach_prompt(
    session: Dict,
    profile: Dict,
    goal: Dict,
    readiness: Dict,
    recent_sessions: List[Dict]
) -> str:
    """构造AI教练的prompt - 把所有context注入"""
    weakest = readiness.get("weakest", "unknown")
    weakest_cn = DIMENSION_NAMES_CN.get(weakest, weakest)

    age = profile.get("age", "未知")
    weight = profile.get("weight_kg", "未知")

    # 最近5次训练摘要
    recent_summary = []
    for s in recent_sessions[-5:]:
        recent_summary.append(
            f"  - {s.get('date', '?')}: {s.get('distance_km', 0)}km, "
            f"爬升{s.get('ascent_m', 0)}m, RPE={s.get('rpe', '?')}"
        )
    recent_text = "\n".join(recent_summary) if recent_summary else "  (无历史记录)"

    boss_days = goal.get("boss_days", [])

    prompt = f"""你是一位资深耐力自行车教练，专门指导业余选手为长途骑行做准备。

【用户画像】
- 年龄: {age}岁
- 体重: {weight}kg
- 重要提示: 该用户44岁，恢复时间比年轻人需要多24-48小时

【目标】
- {goal.get('name', '环台900km')}: {goal.get('total_distance_km', 900)}km / {goal.get('total_days', 9)}天
- Boss Days (最难三天): Day {boss_days}
- 单日最长: 122km (Day 4)
- 最难一天: 112km + 900m爬升 (Day 6 壽卡)

【6个准备度维度说明】
- 周均训练量 (Volume): 近4周周均km
- 单次耐力 (Endurance): 近30天最长单次距离
- 爬升能力 (Climbing): 近4周周均爬升米数
- 训练一致性 (Consistency): 每周训练天数
- 恢复/背靠背能力 (Recovery): 最长连续训练天数
- 有氧基础 (Aerobic Base): 近4周RPE≤6的累计训练小时数 (对应运动科学Z2基础训练)

【当前准备度】
- 总分: {readiness.get('total', 0)}%
- 最弱维度: {weakest_cn} ({readiness['dimensions'].get(weakest, {}).get('score', 0)}%)

【本次训练数据】
- 日期: {session.get('date', '?')}
- 距离: {session.get('distance_km', 0)}km
- 爬升: {session.get('ascent_m', 0)}m
- 时长: {session.get('duration_min', 0)}分钟
- 平均速度: {session.get('avg_speed_kmh', 0)}km/h
- 平均心率: {session.get('avg_hr') or '未记录'}
- 平均功率: {session.get('avg_power_w') or '未记录'}
- RPE自评: {session.get('rpe', '?')}/10
- 备注: {session.get('notes', '无')}

【近5次训练】
{recent_text}

请输出严格的JSON对象（不要任何markdown标记），格式如下:
{{
  "verdict": "对本次训练的评价(30字内)",
  "intensity_label": "Z2基础/Z3Tempo/Z4阈值/Z5极限/恢复骑 中选一个",
  "weak_link": "{weakest_cn}",
  "next_focus": "未来3-7天的具体训练建议(60字内，要具体可执行)",
  "warning": "如有过度训练/恢复不足风险则警告，否则空字符串",
  "encouragement": "一句鼓励的话(20字内)"
}}

注意:
1. 如果RPE>=7，优先建议恢复
2. 如果最弱是"有氧基础"，推荐增加低强度长时间骑行 (RPE 3-6, 2-3小时)
3. 如果近期连续高强度，提示44岁需要更长恢复
4. 推荐要具体（如"Dandenong 1in20两次反复"），不要空泛
5. 必须返回有效JSON
"""
    return prompt


def _fallback_analysis(reason: str) -> Dict:
    """AI调用失败时的兜底返回"""
    return {
        "verdict": "本次训练已记录",
        "intensity_label": "未知",
        "weak_link": "未知",
        "next_focus": f"AI分析暂时不可用 ({reason})，但训练数据已保存",
        "warning": "",
        "encouragement": "继续保持训练节奏"
    }


def get_ai_analysis(
    session: Dict,
    profile: Dict,
    goal: Dict,
    readiness: Dict,
    recent_sessions: List[Dict],
    api_key: str,
    model: str = "google/gemini-3.5-flash"
) -> Optional[Dict]:
    """
    调用AI教练，返回训练分析

    ★ try/except 异常处理
    """
    if not api_key:
        return _fallback_analysis("未配置API key")

    prompt = build_coach_prompt(session, profile, goal, readiness, recent_sessions)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/formosa900-readiness",
        "X-Title": "Formosa 900 Readiness Coach"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 2000,
        "reasoning": {"effort": "minimal"}
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return extract_json(content)

    except requests.exceptions.Timeout:
        return _fallback_analysis("AI请求超时")
    except requests.exceptions.RequestException as e:
        return _fallback_analysis(f"AI请求失败: {e}")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return _fallback_analysis(f"AI响应解析失败: {e}")
