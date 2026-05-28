# 🚴 Formosa 900 Readiness Coach

> An AI-powered personal cycling coach to prepare you for the 9-day, 900km tour around Taiwan.

## 🎯 这个工具解决什么真实问题

我（44岁，全职HR Director + 2个孩子的爸）计划2026年底完成捷安特9日环台（900km / 累计爬升~3000m / 最难一天 Day 6 壽卡 112km + 900m）。

市面上的Strava/Garmin都是**记录历史**，无法基于"环台需求"反推我现在差多少。这个工具基于**6个维度**（容量/耐力/爬升/一致性/恢复力/有氧基础）计算**Readiness%**，并由AI教练给出具体的训练重点建议。

## ✨ 核心功能

- 📊 **Readiness% 仪表盘**：实时显示距离环台目标的准备度
- 🎯 **5题初始化评估**：建立基线
- 📸 **截图智能录入**：上传码表截图，AI自动提取距离/爬升/功率等数据
- 🤖 **AI教练分析**：每次训练后给出强度评估和下一步建议
- 📈 **趋势曲线**：可视化进步轨迹

## 🧬 6维度算法（基于运动科学）

| 维度 | 权重 | 含义 |
|---|---|---|
| Volume 容量 | 15% | 近4周周均km |
| Endurance 耐力 | 30% | 近30天最长单次 |
| Climbing 爬升 | 20% | 近4周周均爬升 |
| Consistency 一致性 | 5% | 每周训练天数 |
| Recovery 恢复力 | 20% | 最长连续训练天数 |
| **Aerobic Base 有氧基础** | **10%** | 近4周RPE≤6累计小时数 |

特色设计：
- **Baseline作为floor**：初始问卷答案永远不被覆盖
- **衰减模型**：超过7天不训练开始衰减(最多到70%)
- **有氧基础**：对应80/20金字塔训练模型，奖励高频中短程

## 🛠️ 技术栈

- Python 3.9+
- Streamlit (Web框架，移动端友好)
- OpenRouter API (调用Gemini 3.5 Flash视觉+文本)
- JSON 本地持久化

## ⚙️ 运行方法

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置API key
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 编辑 secrets.toml，填入你的OpenRouter API key

# 4. 启动
streamlit run app.py
```

## ✅ Week 4 技术要素覆盖

- [x] 至少3个自定义函数 → `core/readiness.py` 包含10+个
- [x] 循环 + 条件判断 → `_filter_recent_sessions`, `calc_aerobic_base_score` 等
- [x] 字典存储数据 → session, profile, readiness全是嵌套字典
- [x] try/except 异常处理 → `core/storage.py`, `vision_parser.py`, `ai_coach.py`
- [x] JSON文件持久化 → `data/*.json`
- [x] Git分支开发 + 至少一次merge回main

## 📜 License

MIT
