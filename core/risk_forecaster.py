"""
环台9日Boss Day风险预测器

基于用户当前能力，评估Taiwan每一天的相对风险等级
- 🟢 Low: 完全在能力范围内
- 🟡 Moderate: 需要努力但可控
- 🟠 Hard: 显著超出现有能力，需针对性训练
- 🔴 Critical: 高风险，重点突破

★ 技术要素 1: 多个自定义函数
★ 技术要素 2: 循环 + 条件判断
★ 技术要素 3: 字典存储结果
"""

from typing import List, Dict


# 风险等级阈值 (ratio = 当天需求 / 用户能力)
# v2调整: 收紧阈值，让真正的Boss Day(Day4/6/7)能标红突出
RISK_LOW_THRESHOLD = 0.85       # < 0.85: 舒适，完全在能力范围内
RISK_MODERATE_THRESHOLD = 1.15  # 0.85-1.15: 可控
RISK_HARD_THRESHOLD = 1.4       # 1.15-1.4: 吃力
# > 1.4: 高风险


def get_user_capabilities(profile: Dict, sessions: List[Dict]) -> Dict:
    """
    评估用户的"能力上限"
    取 baseline (问卷答案) 和 实际sessions 中的较大值
    """
    answers = profile.get("initial_answers", {})

    # 来自baseline问卷
    baseline_max_km = answers.get("longest_recent_ride_km", 0)
    baseline_weekly_climb = answers.get("weekly_climb_m", 0)

    # 来自实际session的最大值
    actual_max_km = 0
    actual_max_session_climb = 0
    for s in sessions:
        actual_max_km = max(actual_max_km, s.get("distance_km", 0))
        actual_max_session_climb = max(actual_max_session_climb, s.get("ascent_m", 0))

    # 取较大值作为"能力上限"
    max_distance = max(baseline_max_km, actual_max_km)

    # 单日爬升能力上限 = max(weekly_climb / 2, 单次最大爬升)
    # 假设一周训练能合理分配，单日上限 ≈ 周量的一半
    typical_session_climb = max(baseline_weekly_climb / 2, actual_max_session_climb)

    return {
        "max_distance_km": max(max_distance, 1),
        "max_climb_m_per_session": max(typical_session_climb, 1)
    }


def assess_day_risk(day: Dict, capabilities: Dict) -> Dict:
    """评估单一天的风险等级"""
    day_km = day.get("distance_km", 0)
    day_climb = day.get("climb_m", 0)

    # 计算比例 (需求 / 能力)
    distance_ratio = day_km / capabilities["max_distance_km"]
    climb_ratio = day_climb / capabilities["max_climb_m_per_session"]

    # 取最大的那个比例作为整体风险
    max_ratio = max(distance_ratio, climb_ratio)

    # 判定瓶颈是距离还是爬升
    if distance_ratio > climb_ratio * 1.1:
        bottleneck = "距离"
    elif climb_ratio > distance_ratio * 1.1:
        bottleneck = "爬升"
    else:
        bottleneck = "综合"

    # 分级
    if max_ratio < RISK_LOW_THRESHOLD:
        risk_level, emoji, label = "low", "🟢", "舒适"
    elif max_ratio < RISK_MODERATE_THRESHOLD:
        risk_level, emoji, label = "moderate", "🟡", "可控"
    elif max_ratio < RISK_HARD_THRESHOLD:
        risk_level, emoji, label = "hard", "🟠", "吃力"
    else:
        risk_level, emoji, label = "critical", "🔴", "高风险"

    return {
        "day": day.get("day"),
        "route": f"{day.get('from', '')} → {day.get('to', '')}",
        "distance_km": day_km,
        "climb_m": day_climb,
        "ratio": round(max_ratio, 2),
        "risk_level": risk_level,
        "emoji": emoji,
        "label": label,
        "bottleneck": bottleneck,
        "warning": day.get("warning", "")
    }


def forecast_day_risks(goal: Dict, profile: Dict, sessions: List[Dict]) -> List[Dict]:
    """预测环台9天的风险等级，返回List of dicts"""
    if not profile:
        return []

    capabilities = get_user_capabilities(profile, sessions)
    daily_plan = goal.get("daily_plan", [])

    risks = []
    for day in daily_plan:
        risks.append(assess_day_risk(day, capabilities))
    return risks


def get_top_risk_days(forecasts: List[Dict], n: int = 3) -> List[Dict]:
    """返回风险最高的n天"""
    sorted_by_risk = sorted(forecasts, key=lambda x: x["ratio"], reverse=True)
    return sorted_by_risk[:n]


def generate_training_advice(top_risks: List[Dict]) -> List[str]:
    """根据高风险日生成训练建议"""
    advice_list = []
    for r in top_risks:
        if r["risk_level"] in ["hard", "critical"]:
            if r["bottleneck"] == "爬升":
                advice = f"加强爬升训练 (推荐Dandenong 1in20反复)"
            elif r["bottleneck"] == "距离":
                advice = f"增加长距离训练 (周末≥100km)"
            else:
                advice = f"综合提升训练量和强度"

            advice_list.append(
                f"**Day {r['day']}** ({r['route']}): {r['emoji']} {r['label']} "
                f"— {r['distance_km']}km/{r['climb_m']}m — 瓶颈: {r['bottleneck']} — {advice}"
            )
    return advice_list
