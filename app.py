"""
Formosa 900 Readiness Coach - 主应用入口

5个Tab的Streamlit Web应用:
1. 📊 Dashboard - 准备度概览 + 最近训练
2. 🎯 初始化 - 5题问卷建立baseline
3. 📝 记录训练 - 截图上传或手动录入 + AI分析
4. 📜 历史 - 训练记录列表
5. ℹ️ 关于 - 项目说明 + 9天行程

v2更新:
- Dashboard显示"最近一次训练"卡片（含delta和AI简评）
- 修复tab切换不刷新的问题（用session_state+st.rerun()）
- Readiness算法改为baseline floor + 衰减模型

★ 技术要素1: 函数 (本文件多个render_xxx函数)
★ 技术要素2: 循环+条件 (各种数据展示)
★ 技术要素3: 字典 (session, profile, readiness全是字典)
★ 技术要素4: try/except (在core模块中)
★ 技术要素5: JSON 持久化 (core/storage.py)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Optional, List, Dict
import uuid

from core import storage
from core.readiness import calculate_readiness, calculate_from_baseline
from core.vision_parser import parse_screenshot
from core.ai_coach import get_ai_analysis, DIMENSION_NAMES_CN
from core.assessment import INITIAL_QUESTIONS, build_profile_from_answers


# ============================================
# 页面配置
# ============================================
st.set_page_config(
    page_title="环台900准备度",
    page_icon="🚴",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ============================================
# 工具函数
# ============================================

def get_api_key() -> str:
    """从secrets.toml取OpenRouter API key"""
    try:
        return st.secrets.get("OPENROUTER_API_KEY", "")
    except Exception:
        return ""


def get_model(key: str, default: str) -> str:
    """从secrets取指定模型，不存在则用默认"""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def days_until_goal(goal_date_str: Optional[str]) -> Optional[int]:
    """计算距离目标出发日还有多少天"""
    if not goal_date_str:
        return None
    try:
        goal_date = datetime.strptime(goal_date_str, "%Y-%m-%d").date()
        return (goal_date - date.today()).days
    except ValueError:
        return None


def new_session_id() -> str:
    """生成唯一的session ID"""
    return f"s_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


# ============================================
# Tab 1: Dashboard
# ============================================

def render_dashboard():
    """Dashboard - Readiness%, 倒计时, 弱项, 最近训练, 趋势"""
    st.title("🚴 环台900 准备度")

    profile = storage.load_profile()
    goal = storage.load_goal()
    sessions = storage.load_sessions()

    # 还没初始化 - 显示引导
    if profile is None:
        st.warning("⚠️ 还没完成初始化评估。请到 **🎯 初始化** Tab 开始。")
        st.markdown(f"""
        ### 关于这个工具

        - **目标**: {goal.get('name', '环台900km')}
        - **挑战**: {goal.get('total_distance_km', 900)}km / {goal.get('total_days', 9)}天
        - **最难一天**: Day 6, 壽卡450m + 112km

        这个工具会:
        1. 评估你当前距离环台目标的准备度
        2. 每次训练后基于真实数据更新准备度
        3. AI教练给你具体的下一步训练建议
        """)
        return

    # 计算Readiness% (v2算法：传入profile让baseline作为floor)
    readiness = calculate_readiness(sessions, goal, profile)

    # ----- 顶部3个核心指标 -----
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="准备度 Readiness", value=f"{readiness['total']}%")

    with col2:
        days_left = days_until_goal(profile.get("goal_date"))
        if days_left is not None:
            display = f"{days_left}天" if days_left >= 0 else "已过期"
            st.metric(label="距离出发", value=display)
        else:
            st.metric(label="距离出发", value="未设定")

    with col3:
        weakest = readiness["weakest"]
        weakest_cn = DIMENSION_NAMES_CN.get(weakest, weakest)
        weakest_score = readiness["dimensions"][weakest]["score"]
        st.metric(label="最弱维度", value=weakest_cn,
                  delta=f"{weakest_score}%", delta_color="off")

    # ----- 衰减提示 (如果距上次训练>7天) -----
    days_since = readiness.get("days_since_last_ride")
    decay = readiness.get("decay_factor", 1.0)
    if days_since is not None and days_since > 7:
        if decay < 1.0:
            st.warning(
                f"⏰ 已 {days_since} 天未训练，体能衰减系数 {int(decay*100)}%。"
                f"建议尽快恢复训练以阻止衰减。"
            )

    st.divider()

    # ----- 最近一次训练卡片 (v2新增) -----
    if sessions:
        last = sessions[-1]
        last_date = last.get("date", "未知")
        last_km = last.get("distance_km", 0)
        last_ascent = last.get("ascent_m", 0)
        last_rpe = last.get("rpe", "?")
        delta = last.get("readiness_delta")
        ai = last.get("ai_analysis") or {}

        with st.container():
            st.subheader("📌 最近一次训练")
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.markdown(
                    f"**{last_date}** · {last_km}km · 爬升 {last_ascent}m · RPE {last_rpe}"
                )
                verdict = ai.get("verdict", "")
                if verdict:
                    st.markdown(f"🤖 *{verdict}*")
            with col_b:
                if delta is not None:
                    sign = "+" if delta >= 0 else ""
                    color = "normal" if delta >= 0 else "inverse"
                    label = "对准备度贡献"
                    st.metric(label, f"{sign}{delta:.1f}%", delta_color=color)

        st.divider()

    # ----- 5维度详情 -----
    st.subheader("📊 5维度详情")

    for dim_key, dim_info in readiness["dimensions"].items():
        score = dim_info["score"]
        weight_pct = int(dim_info["weight"] * 100)
        cn_name = DIMENSION_NAMES_CN.get(dim_key, dim_key)
        st.markdown(f"**{cn_name}** (权重 {weight_pct}%)")
        st.progress(int(score) / 100, text=f"{score}%")

    st.divider()

    # ----- 趋势曲线 -----
    if len([s for s in sessions if "readiness_after" in s]) >= 2:
        st.subheader("📈 准备度趋势")
        plot_readiness_trend(sessions)


def plot_readiness_trend(sessions: List[Dict]):
    """绘制Readiness%随时间变化的曲线"""
    data = []
    for s in sessions:
        if "readiness_after" in s and s.get("date"):
            data.append({
                "date": s["date"],
                "Readiness%": s["readiness_after"]
            })

    if len(data) < 2:
        st.info("至少需要2次记录才能显示趋势")
        return

    df = pd.DataFrame(data).sort_values("date").set_index("date")
    st.line_chart(df, y="Readiness%")


# ============================================
# Tab 2: Initialization
# ============================================

def render_initialization():
    """初始化评估 - 基本信息 + 5题问卷"""
    st.title("🎯 初始化评估")

    profile = storage.load_profile()

    if profile is not None:
        st.success("✅ 你已经完成过初始化")
        if st.button("🔄 重置并重新评估", type="secondary"):
            storage.reset_all()
            # 清除可能残留的session_state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.markdown("---")
        st.markdown("**当前画像:**")
        st.json(profile)
        return

    st.markdown("回答以下问题，建立你的初始baseline。")

    # ----- 基本信息 -----
    with st.expander("👤 基本信息", expanded=True):
        name = st.text_input("称呼", value="Cyclist")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("年龄", min_value=10, max_value=99, value=40, step=1)
            weight = st.number_input("体重 (kg)", min_value=30, max_value=150, value=70, step=1)
        with col2:
            gender = st.selectbox("性别", ["男", "女", "其他"])
            height = st.number_input("身高 (cm)", min_value=120, max_value=220, value=175, step=1)

        goal_date = st.date_input(
            "目标环台出发日期",
            value=date(2026, 12, 1),
            min_value=date.today()
        )

    # ----- 5题问卷 -----
    st.markdown("---")
    st.subheader("📋 体能状态评估 (5题)")

    answers = {}

    q = INITIAL_QUESTIONS["weekly_km"]
    answers["weekly_km"] = st.number_input(
        q["label"], min_value=q["min"], max_value=q["max"],
        value=q["default"], step=q["step"], help=q["help"]
    )

    q = INITIAL_QUESTIONS["longest_recent_ride_km"]
    answers["longest_recent_ride_km"] = st.number_input(
        q["label"], min_value=q["min"], max_value=q["max"],
        value=q["default"], step=q["step"], help=q["help"]
    )

    q = INITIAL_QUESTIONS["weekly_climb_m"]
    answers["weekly_climb_m"] = st.number_input(
        q["label"], min_value=q["min"], max_value=q["max"],
        value=q["default"], step=q["step"], help=q["help"]
    )

    q = INITIAL_QUESTIONS["training_days_per_week"]
    answers["training_days_per_week"] = st.number_input(
        q["label"], min_value=q["min"], max_value=q["max"],
        value=q["default"], step=q["step"], help=q["help"]
    )

    q = INITIAL_QUESTIONS["can_do_back_to_back"]
    back_to_back_choice = st.radio(q["label"], q["options"], help=q["help"])
    answers["can_do_back_to_back"] = (back_to_back_choice == "可以")

    st.markdown("---")

    if st.button("✅ 完成评估", type="primary"):
        user_info = {
            "name": name, "age": age, "gender": gender,
            "weight_kg": weight, "height_cm": height,
            "goal_date": goal_date.strftime("%Y-%m-%d")
        }
        new_profile = build_profile_from_answers(answers, user_info)
        if storage.save_profile(new_profile):
            st.success("🎉 评估完成！前往 **📊 Dashboard** 查看你的准备度。")
            st.balloons()
        else:
            st.error("保存失败，请检查data目录权限")


# ============================================
# Tab 3: Record Training
# ============================================

def render_record():
    """记录训练 - 截图上传或手动 + AI分析"""
    st.title("📝 记录训练")

    profile = storage.load_profile()
    if profile is None:
        st.warning("请先完成 **🎯 初始化评估**")
        return

    goal = storage.load_goal()
    sessions = storage.load_sessions()

    # ----- 显示刚保存的训练结果 (v2: 用session_state持久化) -----
    if "recently_saved" in st.session_state:
        saved = st.session_state["recently_saved"]
        delta = saved.get("delta", 0)
        sign = "+" if delta >= 0 else ""

        st.success(
            f"✅ 已保存 {saved['date']} 的训练记录。"
            f"准备度 {saved['readiness_before']:.1f}% → **{saved['readiness_after']:.1f}%** "
            f"({sign}{delta:.1f}%)"
        )

        ai_result = saved.get("ai_result") or {}
        if ai_result:
            st.markdown("### 🤖 AI教练分析")
            col_a, col_b = st.columns(2)
            with col_a:
                st.info(f"**评价**: {ai_result.get('verdict', '')}")
                st.markdown(f"**强度区间**: {ai_result.get('intensity_label', '')}")
            with col_b:
                weak = ai_result.get('weak_link', '')
                st.warning(f"**当前最弱**: {weak}")

            st.markdown(f"**🎯 下一步训练重点**: {ai_result.get('next_focus', '')}")

            warning = ai_result.get('warning', '').strip()
            if warning:
                st.error(f"⚠️ {warning}")

            encouragement = ai_result.get('encouragement', '').strip()
            if encouragement:
                st.markdown(f"> 💪 *{encouragement}*")

        if st.button("📝 记录新一次训练"):
            del st.session_state["recently_saved"]
            if "extracted_data" in st.session_state:
                del st.session_state["extracted_data"]
            st.rerun()
        return

    # ----- 选择输入模式 -----
    input_mode = st.radio(
        "选择录入方式:",
        ["📸 上传码表截图 (推荐)", "✏️ 手动输入"],
        horizontal=True
    )

    extracted_data = st.session_state.get("extracted_data", {})

    # ----- 模式1: 截图上传 -----
    if input_mode == "📸 上传码表截图 (推荐)":
        uploaded = st.file_uploader(
            "上传码表/骑行APP截图",
            type=["png", "jpg", "jpeg"],
            help="支持Garmin/Wahoo/Bryton/Hammerhead/Strava等"
        )

        if uploaded is not None:
            st.image(uploaded, width=300, caption="已上传")

            if st.button("🤖 AI解析截图", type="primary"):
                api_key = get_api_key()
                model = get_model("DEFAULT_VISION_MODEL", "google/gemini-3.5-flash")

                if not api_key:
                    st.error("⚠️ 未配置OpenRouter API key。请在 `.streamlit/secrets.toml` 添加。")
                else:
                    with st.spinner("AI正在解析截图..."):
                        image_bytes = uploaded.getvalue()
                        result = parse_screenshot(image_bytes, api_key, model)

                    if result:
                        st.session_state["extracted_data"] = result
                        st.success("✅ 解析完成！请在下方确认/修改数据")
                        extracted_data = result
                    else:
                        st.error("解析失败，请尝试手动输入")

    # ----- 数据确认/编辑表单 -----
    st.markdown("---")
    st.subheader("确认/输入数据")

    col1, col2 = st.columns(2)

    with col1:
        d = st.date_input("日期", value=date.today())
        distance = st.number_input(
            "距离 (km)", min_value=0.0, max_value=500.0,
            value=float(extracted_data.get("distance_km") or 0), step=0.1
        )
        duration = st.number_input(
            "时长 (分钟)", min_value=0, max_value=1440,
            value=int(extracted_data.get("active_duration_min") or 0), step=1
        )
        ascent = st.number_input(
            "爬升 (m)", min_value=0, max_value=10000,
            value=int(extracted_data.get("ascent_m") or 0), step=1
        )
        avg_speed = st.number_input(
            "平均速度 (km/h)", min_value=0.0, max_value=80.0,
            value=float(extracted_data.get("avg_speed_kmh") or 0), step=0.1
        )

    with col2:
        avg_hr_val = extracted_data.get("avg_hr")
        avg_hr = st.number_input(
            "平均心率 (可选)", min_value=0, max_value=250,
            value=int(avg_hr_val) if avg_hr_val else 0, step=1
        )
        avg_power_val = extracted_data.get("avg_power_w")
        avg_power = st.number_input(
            "平均功率 W (可选)", min_value=0, max_value=600,
            value=int(avg_power_val) if avg_power_val else 0, step=1
        )
        np_val = extracted_data.get("normalized_power_w")
        norm_power = st.number_input(
            "标准化功率 W (可选)", min_value=0, max_value=600,
            value=int(np_val) if np_val else 0, step=1
        )
        cadence_val = extracted_data.get("cadence")
        cadence = st.number_input(
            "踏频 (可选)", min_value=0, max_value=150,
            value=int(cadence_val) if cadence_val else 0, step=1
        )

    st.markdown("**主观感受**")
    rpe = st.slider(
        "RPE 自评 (1=极轻松, 10=极限)",
        min_value=1, max_value=10, value=5,
        help="RPE = Rate of Perceived Exertion，你主观感觉的强度"
    )
    notes = st.text_area("备注 (可选)", placeholder="路线、天气、感觉等...")

    st.markdown("---")

    if st.button("💾 保存并AI分析", type="primary"):
        if distance <= 0:
            st.error("距离必须大于0")
            return

        # 构造session记录
        session = {
            "id": new_session_id(),
            "date": d.strftime("%Y-%m-%d"),
            "distance_km": distance,
            "duration_min": duration,
            "ascent_m": ascent,
            "avg_speed_kmh": avg_speed,
            "avg_hr": avg_hr if avg_hr > 0 else None,
            "avg_power_w": avg_power if avg_power > 0 else None,
            "normalized_power_w": norm_power if norm_power > 0 else None,
            "cadence": cadence if cadence > 0 else None,
            "rpe": rpe,
            "notes": notes,
            "created_at": datetime.now().isoformat()
        }

        # v2: 计算before/after并存储delta
        readiness_before = calculate_readiness(sessions, goal, profile)
        sessions_with_new = sessions + [session]
        readiness_after = calculate_readiness(sessions_with_new, goal, profile)
        delta = readiness_after["total"] - readiness_before["total"]

        # 调AI分析
        api_key = get_api_key()
        coach_model = get_model("DEFAULT_COACH_MODEL", "google/gemini-3.5-flash")

        with st.spinner("AI教练正在分析..."):
            ai_result = get_ai_analysis(
                session, profile, goal, readiness_after, sessions,
                api_key, coach_model
            )

        session["ai_analysis"] = ai_result
        session["readiness_after"] = readiness_after["total"]
        session["readiness_before"] = readiness_before["total"]
        session["readiness_delta"] = round(delta, 1)

        # 持久化
        if storage.append_session(session):
            # 存入session_state以便rerun后还能显示
            st.session_state["recently_saved"] = {
                "date": session["date"],
                "ai_result": ai_result,
                "readiness_before": readiness_before["total"],
                "readiness_after": readiness_after["total"],
                "delta": round(delta, 1)
            }

            # 清除截图缓存
            if "extracted_data" in st.session_state:
                del st.session_state["extracted_data"]

            # ★ 强制全页rerun，Dashboard用新数据渲染
            st.rerun()
        else:
            st.error("保存失败")


# ============================================
# Tab 4: History
# ============================================

def render_history():
    """训练历史 - 倒序展示所有session"""
    st.title("📜 训练历史")

    sessions = storage.load_sessions()

    if not sessions:
        st.info("还没有训练记录，去 **📝 记录训练** 录入第一次吧")
        return

    st.markdown(f"共 **{len(sessions)}** 次记录")

    for s in reversed(sessions):
        with st.expander(
            f"📅 {s.get('date')} - {s.get('distance_km')}km / "
            f"爬升 {s.get('ascent_m')}m / RPE {s.get('rpe')}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"- 时长: {s.get('duration_min')}分钟")
                st.markdown(f"- 平均速度: {s.get('avg_speed_kmh')}km/h")
                if s.get("avg_hr"):
                    st.markdown(f"- 平均心率: {s.get('avg_hr')}")
                if s.get("avg_power_w"):
                    st.markdown(f"- 平均功率: {s.get('avg_power_w')}W")
            with col2:
                if s.get("readiness_after") is not None:
                    st.metric("此次后准备度", f"{s['readiness_after']}%")
                delta = s.get("readiness_delta")
                if delta is not None:
                    sign = "+" if delta >= 0 else ""
                    st.caption(f"变化: {sign}{delta:.1f}%")

            if s.get("notes"):
                st.markdown(f"**备注**: {s.get('notes')}")

            ai = s.get("ai_analysis") or {}
            if ai:
                st.markdown("**🤖 AI分析**:")
                st.markdown(f"- 评价: {ai.get('verdict', '')}")
                st.markdown(f"- 下一步: {ai.get('next_focus', '')}")


# ============================================
# Tab 5: About
# ============================================

def render_about():
    """项目介绍 + 9天行程展示 + 重置工具"""
    st.title("ℹ️ 关于本项目")

    goal = storage.load_goal()

    st.markdown(f"""
    ### Formosa 900 准备度 AI 教练

    这个工具帮你训练直至准备好完成 **{goal.get('name', '环台900')}**。

    **与Strava/Garmin不同——它以终为始**: 先定义环台的具体要求，再倒推你今天差多少。
    """)

    st.subheader("🗺️ 9天行程")

    plan = goal.get("daily_plan", [])
    rows = []
    for d in plan:
        rows.append({
            "Day": d.get("day"),
            "路线": f"{d.get('from')} → {d.get('to')}",
            "距离": f"{d.get('distance_km')}km",
            "爬升": f"{d.get('climb_m')}m",
            "难度": d.get("difficulty"),
            "关键": d.get("warning", "")
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    boss = goal.get("boss_days", [])
    st.markdown(f"**🔥 Boss Days (最难三天)**: Day {boss}")

    st.divider()

    st.subheader("🔧 工具栏")
    if st.button("⚠️ 重置所有数据 (谨慎)", type="secondary"):
        storage.reset_all()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("已重置")
        st.rerun()


# ============================================
# 主入口
# ============================================

def main():
    """主入口 - 5个Tab组成的Streamlit应用"""
    storage.ensure_data_dir()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", "🎯 初始化", "📝 记录训练", "📜 历史", "ℹ️ 关于"
    ])

    with tab1:
        render_dashboard()
    with tab2:
        render_initialization()
    with tab3:
        render_record()
    with tab4:
        render_history()
    with tab5:
        render_about()


if __name__ == "__main__":
    main()
