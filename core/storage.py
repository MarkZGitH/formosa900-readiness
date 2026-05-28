"""
存储层 - 负责所有JSON文件的读写操作

★ 技术要素 4: try/except 异常处理
★ 技术要素 5: JSON 文件本地存储
"""

import json
import os
from typing import Optional, Dict, List, Any

# 数据文件路径常量
DATA_DIR = "data"
GOAL_FILE = os.path.join(DATA_DIR, "goal.json")
PROFILE_FILE = os.path.join(DATA_DIR, "user_profile.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")


def ensure_data_dir() -> None:
    """确保 data/ 目录存在，没有就创建"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_json(file_path: str, default: Any = None) -> Any:
    """
    从指定路径读取JSON文件
    如果文件不存在或解析失败，返回default值

    ★ try/except 异常处理示例 - 处理3种典型错误
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 文件不存在 - 第一次运行时是正常情况
        return default
    except json.JSONDecodeError as e:
        # 文件存在但JSON格式损坏
        print(f"⚠️ JSON文件损坏 {file_path}: {e}")
        return default
    except Exception as e:
        # 兜底处理其他未知错误
        print(f"⚠️ 读取文件失败 {file_path}: {e}")
        return default


def save_json(file_path: str, data: Any) -> bool:
    """保存数据到JSON文件，返回是否成功"""
    try:
        ensure_data_dir()
        with open(file_path, 'w', encoding='utf-8') as f:
            # ensure_ascii=False 让中文不被转义；indent=2 让文件可读
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ 保存文件失败 {file_path}: {e}")
        return False


# ----- 下面是针对3种数据的便捷封装 -----

def load_goal() -> Dict:
    """读取环台目标定义"""
    return load_json(GOAL_FILE, default={})


def load_profile() -> Optional[Dict]:
    """读取用户档案，没有则返回None（表示需要初始化）"""
    return load_json(PROFILE_FILE, default=None)


def save_profile(profile: Dict) -> bool:
    """保存用户档案"""
    return save_json(PROFILE_FILE, profile)


def load_sessions() -> List[Dict]:
    """读取所有训练记录"""
    return load_json(SESSIONS_FILE, default=[])


def save_sessions(sessions: List[Dict]) -> bool:
    """保存所有训练记录"""
    return save_json(SESSIONS_FILE, sessions)


def append_session(session: Dict) -> bool:
    """追加一条训练记录"""
    sessions = load_sessions()
    sessions.append(session)
    return save_sessions(sessions)


def reset_all() -> None:
    """
    重置所有用户数据（保留goal.json）
    用于"换一个用户使用"或"重新开始"
    """
    for f in [PROFILE_FILE, SESSIONS_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                print(f"⚠️ 删除文件失败 {f}: {e}")
