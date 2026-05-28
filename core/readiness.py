"""
Readiness% 计算引擎 - v3 (新增Aerobic Base维度)

6个维度: Volume / Endurance / Climbing / Consistency / Recovery / Aerobic Base

v3更新:
- 新增第6维度"有氧基础"，对应运动科学Z2基础训练理论 (80/20金字塔模型)
- 权重重新分配: Volume 15%, Consistency 5%, 新增 Aerobic Base 10%
- baseline估算: weekly_km / 26 × 4 × 0.8 推算4周低强度训练小时数
- 单次训练RPE ≤ 6 时计入Aerobic Base，防止高强度刷分

★ 技术要素 1: 多个自定义函数 (本文件10+个函数)
★ 技术要素 2: 循环 + 条件判断
★ 技术要素 3: 字典存储结果
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta


# ============================================
# 算法常量
# ============================================

# 业余车手混合配速 (通勤+长骑+爬山的平均, km/h)
# 用于从 weekly_km 估算训练总小时数
AVG_SPEED_KMH = 26

# RPE阈值: ≤ 此值算低强度有氧 (Z2基础)
LOW_INTENSITY_RPE_THRESHOLD = 6

# 总训练时长中估算为低强度的比例 (baseline推算用)
LOW_INTENSITY_RATIO = 0.8

# Aerobic Base 4周目标小时数
AEROBIC_BASE_TARGET_HOURS = 30


def _parse_date(date_str: str) -> datetime:
    """把ISO格式日期字符串转成datetime对象"""
    return datetime.strptime(date_str, "%Y-%m-%d")


def _filter_recent_sessions(sessions: List[Dict], days: int) -> List[Dict]:
    """
    返回近 days 天内的训练记录

    ★ 循环 + 条件判断示例
    """
    if not sessions:
        return []

    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for s in sessions:
        try:
            session_date = _parse_date(s.get("date", "1970-01-01"))
            if session_date >= cutoff:
                recent.append(s)
        except ValueError:
            continue
    return recent


def _days_since_last_ride(sessions: List[Dict]) -> Optional[int]:
    """返回距离最后一次训练的天数，没有session时返回None"""
    if not sessions:
        return None
    last_date = None
    for s in sessions:
        date_str = s.get("date")
        if not date_str:
            continue
        try:
            d = _parse_date(date_str).date()
            if last_date is None or d > last_date:
                last_date = d
        except ValueError:
            continue
    if last_date is None:
        return None
    return (datetime.now().date() - last_date).days


def compute_decay_factor(sessions: List[Dict]) -> float:
    """
    根据距离最后一次训练的天数计算衰减系数
    - 0-7天: 不衰减 (1.0)
    - 8-28天: 线性衰减到70%
    - >28天: 固定70%
    """
    days_since = _days_since_last_ride(sessions)
    if days_since is None:
        return 1.0
    if days_since <= 7:
        return 1.0
    elif days_since <= 28:
        return 1.0 - (days_since - 7) / 21.0 * 0.3
    else:
        return 0.7


# ============================================
# 6个维度的计算函数
# ============================================

def calc_volume_score(sessions: List[Dict], target_weekly_km: float = 250.0) -> float:
    """维度1: Volume - 近4周周均km / 目标周km × 100"""
    recent = _filter_recent_sessions(sessions, days=28)
    total_km = sum(s.get("distance_km", 0) for s in recent)
    weekly_avg = total_km / 4.0
    score = min(100.0, weekly_avg / target_weekly_km * 100)
    return round(score, 1)


def calc_endurance_score(sessions: List[Dict], target_single_km: float = 125.0) -> float:
    """维度2: Endurance - 近30天最长单次 / 目标单次"""
    recent = _filter_recent_sessions(sessions, days=30)
    if not recent:
        return 0.0
    longest = max(s.get("distance_km", 0) for s in recent)
    score = min(100.0, longest / target_single_km * 100)
    return round(score, 1)


def calc_climbing_score(sessions: List[Dict], target_weekly_m: float = 2500.0) -> float:
    """维度3: Climbing - 近4周周均爬升 / 目标周爬升"""
    recent = _filter_recent_sessions(sessions, days=28)
    total_climb = sum(s.get("ascent_m", 0) for s in recent)
    weekly_avg = total_climb / 4.0
    score = min(100.0, weekly_avg / target_weekly_m * 100)
    return round(score, 1)


def calc_consistency_score(sessions: List[Dict], target_days_per_week: float = 5.0) -> float:
    """维度4: Consistency - 近4周每周训练天数"""
    recent = _filter_recent_sessions(sessions, days=28)
    unique_dates = set()
    for s in recent:
        date_str = s.get("date")
        if date_str:
            unique_dates.add(date_str)
    days_per_week = len(unique_dates) / 4.0
    score = min(100.0, days_per_week / target_days_per_week * 100)
    return round(score, 1)


def calc_recovery_score(sessions: List[Dict], target_consecutive: int = 5) -> float:
    """维度5: Recovery - 近30天最长连续训练天数"""
    recent = _filter_recent_sessions(sessions, days=30)
    if not recent:
        return 0.0

    dates_set = set()
    for s in recent:
        d = s.get("date")
        if d:
            try:
                dates_set.add(_parse_date(d).date())
            except ValueError:
                continue

    if not dates_set:
        return 0.0

    sorted_dates = sorted(dates_set)
    max_streak = 1
    current_streak = 1
    for i in range(1, len(sorted_dates)):
        diff = (sorted_dates[i] - sorted_dates[i - 1]).days
        if diff == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1

    score = min(100.0, max_streak / target_consecutive * 100)
    return round(score, 1)


def calc_aerobic_base_score(
    sessions: List[Dict],
    target_hours: float = AEROBIC_BASE_TARGET_HOURS,
    rpe_threshold: int = LOW_INTENSITY_RPE_THRESHOLD
) -> float:
    """
    维度6: Aerobic Base 有氧基础 ★ 新增

    近4周内 RPE ≤ 阈值 的训练总时长(小时) / 目标小时数 × 100

    对应运动科学Z2基础训练理论:
    - 80/20金字塔模型中"底座"部分
    - 高频中短程通勤恰好覆盖这个区间(RPE 3-5)
    - 高强度训练(RPE > 6)不计入此维度，防止"刷分"
    """
    recent = _filter_recent_sessions(sessions, days=28)

    # 累计低强度训练分钟数
    total_minutes = 0
    for s in recent:
        rpe = s.get("rpe")
        duration = s.get("duration_min", 0)
        # 只统计RPE填了的且≤阈值的训练
        if rpe is not None and rpe <= rpe_threshold and duration > 0:
            total_minutes += duration

    total_hours = total_minutes / 60.0
    score = min(100.0, total_hours / target_hours * 100)
    return round(score, 1)


# ============================================
# 主入口
# ============================================

def calculate_from_baseline(profile: Dict, goal: Dict) -> Dict:
    """
    从初始化问卷答案直接计算baseline Readiness%

    Aerobic Base维度通过weekly_km推算:
      4周低强度小时数 = weekly_km / 26 × 4 × 0.8
    """
    answers = profile.get("initial_answers", {})
    req = goal.get("derived_requirements", {})
    weights = req.get("weights", {
        "volume": 0.15, "endurance": 0.30, "climbing": 0.20,
        "consistency": 0.05, "recovery": 0.20, "aerobic_base": 0.10
    })

    weekly_km = answers.get("weekly_km", 0)
    longest_recent_km = answers.get("longest_recent_ride_km", 0)
    weekly_climb_m = answers.get("weekly_climb_m", 0)
    training_days = answers.get("training_days_per_week", 0)
    back_to_back = answers.get("can_do_back_to_back", False)

    # 推算4周低强度有氧训练小时数
    # 公式: weekly_km / AVG_SPEED_KMH = 周小时数; ×4 = 4周; ×0.8 = 低强度部分
    estimated_4w_aerobic_hours = (weekly_km / AVG_SPEED_KMH) * 4 * LOW_INTENSITY_RATIO
    target_aerobic = req.get("min_aerobic_base_hours_4w", AEROBIC_BASE_TARGET_HOURS)

    scores = {
        "volume": min(100.0, weekly_km / req.get("min_weekly_volume_km", 250) * 100),
        "endurance": min(100.0, longest_recent_km / req.get("min_single_ride_km", 125) * 100),
        "climbing": min(100.0, weekly_climb_m / req.get("min_weekly_climb_m", 2500) * 100),
        "consistency": min(100.0, training_days / 5.0 * 100),
        "recovery": 60.0 if back_to_back else 30.0,
        "aerobic_base": min(100.0, estimated_4w_aerobic_hours / target_aerobic * 100)
    }

    dimensions = {}
    total = 0.0
    for dim, score in scores.items():
        w = weights.get(dim, 0.0)
        weighted = score * w
        total += weighted
        dimensions[dim] = {
            "score": round(score, 1),
            "weight": w,
            "weighted": round(weighted, 1)
        }

    weakest = min(scores, key=scores.get)

    return {
        "total": round(total, 1),
        "dimensions": dimensions,
        "weakest": weakest
    }


def calculate_readiness(
    sessions: List[Dict],
    goal: Dict,
    profile: Optional[Dict] = None
) -> Dict:
    """
    综合计算Readiness% (v3 - 6维度)

    设计原则:
    1. 计算actual (实际训练) 和 baseline (问卷)
    2. 每个维度取 max(actual, baseline) - baseline作为floor
    3. 应用衰减系数 (基于距上次训练天数)
    """
    req = goal.get("derived_requirements", {})
    target_weekly_km = req.get("min_weekly_volume_km", 250)
    target_single_km = req.get("min_single_ride_km", 125)
    target_weekly_climb = req.get("min_weekly_climb_m", 2500)
    target_aerobic = req.get("min_aerobic_base_hours_4w", AEROBIC_BASE_TARGET_HOURS)
    weights = req.get("weights", {
        "volume": 0.15, "endurance": 0.30, "climbing": 0.20,
        "consistency": 0.05, "recovery": 0.20, "aerobic_base": 0.10
    })

    # 1. 计算actual scores
    actual_scores = {
        "volume": calc_volume_score(sessions, target_weekly_km),
        "endurance": calc_endurance_score(sessions, target_single_km),
        "climbing": calc_climbing_score(sessions, target_weekly_climb),
        "consistency": calc_consistency_score(sessions),
        "recovery": calc_recovery_score(sessions),
        "aerobic_base": calc_aerobic_base_score(sessions, target_aerobic)
    }

    # 2. 计算baseline scores
    baseline_scores = {}
    if profile:
        baseline_result = calculate_from_baseline(profile, goal)
        for dim, info in baseline_result["dimensions"].items():
            baseline_scores[dim] = info["score"]

    # 3. 合并: max(actual, baseline)
    merged = {}
    for dim, actual_val in actual_scores.items():
        base_val = baseline_scores.get(dim, 0)
        merged[dim] = max(actual_val, base_val)

    # 4. 应用衰减
    decay = compute_decay_factor(sessions)
    final_scores = {dim: round(merged[dim] * decay, 1) for dim in merged}

    # 5. 加权求和
    dimensions = {}
    total = 0.0
    for dim, score in final_scores.items():
        w = weights.get(dim, 0.0)
        weighted = score * w
        total += weighted
        dimensions[dim] = {
            "score": score,
            "weight": w,
            "weighted": round(weighted, 1)
        }

    weakest = min(final_scores, key=final_scores.get)
    days_since = _days_since_last_ride(sessions)

    return {
        "total": round(total, 1),
        "dimensions": dimensions,
        "weakest": weakest,
        "decay_factor": round(decay, 2),
        "days_since_last_ride": days_since
    }
