# 🚴 Formosa 900 Readiness Coach

> 一个AI驱动的个人骑行教练，帮我（和任何业余车友）准备好完成9天900公里的环台湾挑战。
>
> *An AI-powered cycling coach that tells you exactly how ready you are for Taiwan's 900km round-island tour — and what to train next.*

---

## 🎯 这个工具解决我的什么真实问题

我有一个人生目标：**2026年底完成9日环台骑行**——900公里、9天、累计爬升约3000米，最难的Day 6要翻越壽卡（450m爬坡 + 当天112km）。

但现实是：我工作日的时间只够20-30km的短途训练（爆发力），周末才偶尔有长途训练（有氧耐力）机会。

我有Wahoo码表，有Strava App，**但它们只会告诉我"骑了多少"，没有一个能回答我最关心的问题**：

> 以我现在的状态，到年底我真的能完成环台吗？还差多少？我下一步该练什么？

所以我做了这个工具。

## 🗺️ 我的目标：环台9天行程

这就是我要征服的900公里。每一天的里程和爬升，决定了我需要练成什么样：

| Day | 路线 | 里程 | 爬升 | 难度 |
|:---:|---|:---:|:---:|---|
| 1 | 台北 → 新竹 | 88 km | 300 m | 🟢 适应 |
| 2 | 新竹 → 台中 | 99 km | 250 m | 🟢 平缓 |
| 3 | 台中 → 嘉义 | 96 km | 100 m | 🟡 撞墙期 |
| 4 | 嘉义 → 高雄 | **122 km** | 150 m | 🔴 全程最长 |
| 5 | 高雄 → 恒春 | 101 km | 350 m | 🟡 丘陵预热 |
| 6 | 恒春 → 知本 | 112 km | **900 m** | 🔴 壽卡爬坡 |
| 7 | 知本 → 瑞穗 | 118 km | 500 m | 🔴 东部最长 |
| 8 | 瑞穗 → 礁溪 | 80 km | 100 m | 🟢 含火车段 |
| 9 | 礁溪 → 台北 | 84 km | 250 m | 🟢 凯旋日 |
| **合计** | **环岛一周** | **~900 km** | **~2900 m** | **9天连续** |

**三大Boss Day**：Day 4（单日最长122km）、Day 6（壽卡900m爬升）、Day 7（东部最长118km）。这三天，就是我训练时要重点突破的目标。

## 💡 核心理念：以终为始（Goal-Driven）

市面上所有运动App都是 **"以始为终"**——记录你做过什么，给你历史趋势。

这个工具反过来，**"以终为始"**：

```
先定义环台需要什么能力  →  再倒推我自己现在差多少  →  AI告诉我下一步练什么
```

## ✨ 核心功能

| 功能 | 说明 |
|---|---|
| 📊 **Readiness% 准备度** | 把环台需求拆成6个维度，实时算出我的综合准备度 |
| 📸 **截图智能录入** | 每次训练后，上传码表截图，AI自动识别距离/爬升/功率，无需手敲 |
| 🤖 **AI教练分析** | 每次训练后，给出强度评估 + 个性化的下一步训练重点 |
| 🗺️ **Boss Day风险预测** | 根据我的当前状态，预测环台9天每一天的难度，标出会"爆"的高风险日 |
| 📈 **趋势追踪** | 可视化准备度随训练的变化轨迹 |

## 🧬 6维度算法（基于运动科学）

| 维度 | 权重 | 含义 | 环台依据 |
|---|---|---|---|
| 单次耐力 Endurance | 30% | 近30天最长单次 | Day 4最长122km |
| 爬升能力 Climbing | 20% | 近4周周均爬升 | Day 6壽卡900m |
| 恢复/背靠背 Recovery | 20% | 最长连续训练天数 | 9天连续骑行 |
| 周均训练量 Volume | 15% | 近4周周均km | 整体里程基础 |
| 有氧基础 Aerobic Base | 10% | 近4周RPE≤6累计小时 | 80/20金字塔训练模型 |
| 训练一致性 Consistency | 5% | 每周训练天数 | 规律性 |

**三个设计亮点**：

1. **Baseline作为floor**：初始问卷答案永远作为底线，单次短途骑行不会让准备度暴跌
2. **科学衰减模型**：超过7天不训练才开始衰减（最多到70%），符合体能维持规律
3. **有氧基础维度**：高频中短程通勤也有真实贡献，对应Z2基础训练理论

## 🛠️ 技术栈

- **Python 3.9+**
- **Streamlit** — Web框架，桌面/移动端自适应
- **OpenRouter API** — 调用 Gemini 3.5 Flash 实现视觉识别 + 文本分析
- **JSON** — 本地数据持久化

## ⚙️ 运行方法

```bash
# 1. 克隆仓库
git clone https://github.com/MarkZGitH/formosa900-readiness.git
cd formosa900-readiness

# 2. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置API key
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 编辑 secrets.toml，填入你的 OpenRouter API key

# 5. 启动
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`。手机访问同WiFi下的Network URL即可。

## 📁 项目结构

```
formosa900-readiness/
├── app.py                  # Streamlit主入口（5个Tab）
├── core/
│   ├── readiness.py        # 6维度Readiness%引擎
│   ├── risk_forecaster.py  # Boss Day风险预测
│   ├── ai_coach.py         # AI教练分析
│   ├── vision_parser.py    # 截图视觉识别
│   ├── storage.py          # JSON持久化
│   └── assessment.py       # 初始化问卷
├── data/
│   └── goal.json           # 环台9日目标定义
└── requirements.txt
```

## 🎓 Week 4 技术要素覆盖

- [x] **自定义函数** — `core/readiness.py` 含10+个，`risk_forecaster.py` 含5个
- [x] **循环 + 条件判断** — 维度计算、风险分级、连续天数检测
- [x] **字典存储数据** — session/profile/readiness 全是嵌套字典
- [x] **try/except 异常处理** — 文件IO、API调用、JSON解析全覆盖
- [x] **JSON 本地持久化** — `data/*.json`
- [x] **Git 分支开发** — `feature/boss-day-risk` 分支开发后merge回main

## 📜 License

MIT
