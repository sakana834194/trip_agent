# 旅行行程智能协作（Trip Planner）
## 介绍
本项目演示如何使用 CrewAI 框架，将多个具备不同角色的智能体协同起来，自动化完成旅行规划。当你在多个目的地之间犹豫时，它会帮助你权衡并产出完整行程方案。

作者：

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

## 运行方式
默认使用 GPT-4，请确保你具备相应访问权限。

***提示：** 如未修改，运行将调用 gpt-4，可能产生费用。*

- **配置环境**：复制并填写 ``.env.example``，配置 [Browseless](https://www.browserless.io/)、[Serper](https://serper.dev/) 与 [OpenAI](https://platform.openai.com/api-keys) 的环境变量。
- **安装依赖**：执行 `poetry install --no-root`。
- **运行脚本**：执行 `poetry run python main.py`，按提示输入信息。

## 细节与说明
- **脚本运行**：也可直接执行 `python main.py`，根据提示输入信息。脚本会使用 CrewAI 框架处理你的需求并生成旅行方案。
- **核心文件**：
  - `./main.py`：主入口脚本。
  - `./trip_tasks.py`：任务提示词与定义。
  - `./trip_agents.py`：智能体角色与创建。
  - `./tools`：供智能体使用的工具集合。

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
