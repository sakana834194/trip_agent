# 旅行行程智能协作（Trip Planner）
## 介绍
本项目演示如何使用 CrewAI 框架，将多个具备不同角色的智能体协同起来，自动化完成旅行规划。当你在多个目的地之间犹豫时，它会帮助你权衡并产出完整行程方案。

作者：@sakana834194 origin:By @joaomdmoura

- [CrewAI 框架](#crewai-框架)
- [运行方式](#运行方式)
- [细节与说明](#细节与说明)
- [使用 GPT-3.5](#默认使用-gpt-3.5,请自行更换)
- [结合本地模型 Ollama](#结合本地模型-ollama)
- [贡献](#贡献)
- [支持与联系](#支持与联系)
- [许可证](#许可证)

## CrewAI 框架
CrewAI 用于编排“扮演不同角色”的智能体协作。在此示例中，多个智能体会协作在若干城市中做出选择，并基于你的偏好生成完整的旅行行程。

## 运行方式（Web 前后端）
本项目提供 Web 版（前后端分离）与脚本版两种运行方式：

### 一、前后端分离（推荐）
1) 安装依赖（使用 Poetry）

```bash
poetry install --no-root
```

2) 配置后端与前端

- 后端基础地址（前端直连），#请根据主机地址和端口号配置#
  - 文件：`.streamlit/config.py`
  - 键：`API_BASE_URL = "http://127.0.0.1:9000"` 

- 数据库（后端）
  - 文件：`api/config.py`
  - 键：`DB_URL`
  - 默认示例（MySQL）：`mysql+pymysql://root:root@127.0.0.1:3306/trip_agent?charset=utf8mb4`
  - 如需 SQLite，暂可将 `DB_URL` 置空或改为 `sqlite:///绝对路径/trip_planner.db`

- 可选外部服务与密钥（按需配置到系统环境或 .env）
  - 大模型：`ALI_APIKEY`（Qwen/DashScope 兼容）
  - 检索：`SERPER_API_KEY`（Serper）
  - 抓取：`BROWSERLESS_API_KEY`（Browserless）
  - 行政区与城市：`AMAP_KEY`（高德）

3) 启动后端（FastAPI）

```bash
uvicorn api.server:app --host 你的主机地址 --port 端口号 --reload
```

4) 启动前端（Streamlit）

```bash
streamlit run .streamlit/app.py
```

访问浏览器输出地址即可使用（默认 8501 端口）。

### 二、脚本版（CLI）
- 安装依赖后，运行：

```bash
poetry run python agents/main.py
```

按提示输入参数即可得到行程文本结果。

## 细节与说明
- **脚本运行**：也可直接执行 `python main.py`，根据提示输入信息。脚本会使用 CrewAI 框架处理你的需求并生成旅行方案。
- **核心文件**：
  - `./main.py`：主入口脚本。
  - `./trip_tasks.py`：任务提示词与定义。
  - `./trip_agents.py`：智能体角色与创建。
  - `./tools`：供智能体使用的工具集合。

### Web 架构与关键路径
- 前端：`.streamlit/app.py`（表单/地图与路线可视化/登录与个人空间/Markdown 渲染与 PDF 下载）
- 后端：`api/server.py`（FastAPI 路由） + `api/routes.py`（认证/计划/版本/收藏/再规划/路线）
- 数据库：`api/db.py`（SQLAlchemy 模型与初始化） + `api/config.py`（`DB_URL` 配置）
- 前端直连配置：`.streamlit/config.py`（`API_BASE_URL`）

### 数据库
- 默认使用 `api/config.py` 的 `DB_URL`；示例为 MySQL：`trip_agent` 数据库（需提前创建并授权）。
- 表结构：`users`、`plans`、`plan_versions`、`favorites`（首次启动自动建表）。
- 版本保存：前端在行程生成成功后（登录态）会自动保存一个版本；地图编辑亦可手动“保存当前版本”。

### 常用 API（后端）
- `POST /api/v1/auth/register` 注册 → 返回 `token`
- `POST /api/v1/auth/login` 登录 → 返回 `token`
- `POST /api/v1/plan` 生成行程（返回结构化与 `raw_markdown`）
- `POST /api/v1/plan/ics` 导出 ICS（占位日程，不再重复跑规划）
- `POST /api/v1/plans/save` 保存计划版本（需 `Authorization: Bearer <token>`）
- `GET /api/v1/plans` 列出计划摘要
- `GET /api/v1/plans/{plan_id}/versions` 列出版本
- `POST /api/v1/plans/{plan_id}/favorite` 切换收藏
- `POST /api/v1/plans/replan` 根据反馈再规划（新版本）
- `POST /api/v1/route` 路线估算（输入站点与模式，返回距离/时长与路径）

### 超时与稳定性
- 前端请求超时：默认 300s（`.streamlit/app.py`）
- 后端规划超时：默认 180s（`api/server.py`，超时返回 504）
- 搜索/联网：可在 `api/config.py` 控制各 Agent 是否启用联网与调用预算；也可按需配置 `SERPER_API_KEY`。

### 平台与网络注意事项
- Python 版本：`>=3.10,<3.12`
- Windows + VPN/全局代理：请确保本地回环不走代理；建议设置：

```powershell
$env:NO_PROXY="localhost,127.0.0.1"
# 或永久：
setx NO_PROXY "localhost,127.0.0.1"
```

- 如果 `localhost` 解析缓慢，建议在 `.streamlit/config.py` 使用 `http://你的主机地址:端口号`。
- MySQL：请确认存在数据库 `trip_agent` 且账号具备权限；Windows 可用 HeidiSQL 管理。

### 导出与可视化
- Markdown：前端直接渲染 `raw_markdown`
- PDF 下载：前端将 Markdown 转 HTML 后转 PDF（需要 `markdown` 与 `xhtml2pdf` 依赖）
- ICS：后端返回按天占位的 ICS 文件
- 地图：支持步行/公交/驾车三种模式，支持站点增删/排序与路线重算

### 常见问题（FAQ）
1) 前端报 ReadTimeout（300s）/后端无响应？
   - 降低联网搜索频率或关闭部分 Agent 联网（见 `api/config.py`）。
   - 缩短候选城市/日期范围；或稍增后端超时（`api/server.py`）。

2) 504 规划超时？
   - 表示后端 180s 超时触发，可缩小输入规模或降低联网检索。

3) 登录/注册报错（bcrypt 相关）？
   - 已使用 PBKDF2-SHA256；如历史残留，请清理用户表后重试或新用户名注册。

4) Serper 检索失败/不稳定？
   - 配置 `SERPER_API_KEY`，并适当降低调用次数与超时，或走代理且为 `localhost/127.0.0.1` 设置 NO_PROXY。

5) MySQL 连接失败？
   - 检查 `api/config.py` 的 `DB_URL`，确认主机/端口/库名/字符集；确保数据库已创建、账号有权限。


## 使用 GPT-3.5
CrewAI 允许在创建 Agent 时传入 `llm` 作为“思维引擎”。因此将某个 Agent 从 GPT-4 切换为 GPT-3.5，只需在（`main.py` 中）创建该 Agent 时传入相应的 `llm`。
```python
from langchain.chat_models import ChatOpenAI

# 使用 GPT-3.5
# llm = ChatOpenAI(model='gpt-3.5')  

# 使用国内模型
llm = ChatOpenAI(
    model="openai/你的模型",
    api_key=os.getenv("环境变量名称"), # 获取你的APIKEY
    api_base="api地址",
    temperature=0.3,
)

def local_expert(self):
    return Agent(
        role='本地资深向导',
        goal='为所选城市提供最优洞见与建议',
        backstory="""经验丰富的本地向导，熟知城市景点与风俗文化""",
        tools=[
            SearchTools.search_internet,
            BrowserTools.scrape_and_summarize_website,
        ],
        llm=llm,  # <----- 在此传入 llm
        verbose=True
    )
```

## 结合本地模型 Ollama
CrewAI 支持与本地模型（如 Ollama）集成，以便获得更高的私有化与定制化能力。这对有定制需求或数据隐私要求的场景尤为有用。

### 安装与配置
- **安装 Ollama**：请先在本地正确安装 Ollama，参考官方安装指南。
- **配置 Ollama**：结合你的本地模型进行调优（可通过 Modelfile 调整）。建议尝试将 `Observation` 设为停用词，并调参 `top_p` 与 `temperature`。

### 在 CrewAI 中使用 Ollama
- 实例化本地模型：创建一个 Ollama 模型实例（可指定模型名与 Base URL），例如：

```python
from langchain.llms import Ollama
ollama_openhermes = Ollama(model="agent")
# 在创建 Agent 时将该模型传入：

def local_expert(self):
    return Agent(
        role='本地资深向导',
        goal='为所选城市提供最优洞见与建议',
        backstory="""经验丰富的本地向导，熟知城市景点与风俗文化""",
        tools=[
            SearchTools.search_internet,
            BrowserTools.scrape_and_summarize_website,
        ],
        llm=ollama_openhermes,  # 传入 Ollama 模型
        verbose=True
    )
```

### 使用本地模型的优势
- **隐私**：数据在本地处理，更有利于保护隐私。
- **可定制**：根据具体任务进行定制化调优。
- **性能**：在合适的硬件条件下，可能获得更低延迟。

## 贡献
欢迎通过 Issue 或 PR 参与贡献，完善功能与中文化体验。

## 支持与联系
如遇问题或需要商业支持，请在仓库提交 Issue 或联系维护者。

## 许可证
本项目基于 MIT 许可证开源。
