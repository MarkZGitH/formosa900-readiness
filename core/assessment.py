"""
初始化问卷逻辑 - 5道题建立用户baseline
"""

from typing import Dict
from datetime import datetime


# 初始化问卷题目定义（字典存储所有题目元数据）
INITIAL_QUESTIONS = {
    "weekly_km": {
        "label": "你目前周均骑行公里数？",
        "help": "估算近1-2个月的平均值",
        "default": 100, "min": 0, "max": 1000, "step": 10
    },
    "longest_recent_ride_km": {
        "label": "你近30天最长一次骑行距离 (km)？",
        "help": "如果你近期没有长途，填日常最长",
        "default": 50, "min": 0, "max": 300, "step": 5
    },
    "weekly_climb_m": {
        "label": "你近4周累计爬升大约多少米？",
        "help": "粗略估计即可。一次Dandenong大约500-1000m",
        "default": 1000, "min": 0, "max": 20000, "step": 100
    },
    "training_days_per_week": {
        "label": "你一周通常骑几天？",
        "help": "包括通勤+训练",
        "default": 3, "min": 1, "max": 7, "step": 1
    },
    "can_do_back_to_back": {
        "label": "你能否连续两天各骑80km+？",
        "help": "已经验证过或自评有信心",
        "options": ["可以", "不确定"],
    }
}


def build_profile_from_answers(answers: Dict, user_info: Dict) -> Dict:
    """根据问卷答案 + 用户基本信息，构建完整的profile字典"""
    return {
        "name": user_info.get("name", "Cyclist"),
        "age": user_info.get("age"),
        "gender": user_info.get("gender"),
        "weight_kg": user_info.get("weight_kg"),
        "height_cm": user_info.get("height_cm"),
        "baseline_assessment_date": datetime.now().strftime("%Y-%m-%d"),
        "goal_date": user_info.get("goal_date"),
        "initial_answers": answers
    }
