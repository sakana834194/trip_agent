import os
from crewai import Agent, LLM
from tools.search_tools import SearchTools
from tools.browser_tools import BrowserTools
from tools.calculator_tools import CalculatorTool
from crewai.tools import BaseTool
from api.config import (
  ENABLE_SEARCH_CITY_SELECTION,
  ENABLE_SEARCH_LOCAL_EXPERT,
  ENABLE_SEARCH_CONCIERGE,
)

# llm模型启动，请自行更换
llm = LLM(
    model="openai/qwen-plus",
    api_key=os.getenv("ALI_APIKEY"),
    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.3,
    max_tokens=1500,           # 限制单次生成长度，避免过长输出导致超时
    request_timeout=120        # 单次请求超时时间（秒）
)

# 多agents启动
class TripAgents():

  # 用于评估多个目的地后最终作出抉择的agent
  def city_selection_agent(self):
    tools: list[BaseTool] = [CalculatorTool()]
    if ENABLE_SEARCH_CITY_SELECTION:
      tools = [
        SearchTools.search_tool(),
        BrowserTools.scrape_and_summarize_website,
        CalculatorTool(),
      ]
    return Agent(
        role='目的地甄选专家',
        goal='基于天气、季节与价格选择最佳城市',
        backstory=
        '擅长分析旅行数据以挑选理想目的地的专家',
        tools=tools,
        llm=llm,
        verbose=True)

  # 用于提供本地旅行建议的agent
  def local_expert(self):
    tools: list[BaseTool] = [CalculatorTool()]
    if ENABLE_SEARCH_LOCAL_EXPERT:
      tools = [
        SearchTools.search_tool(),
        BrowserTools.scrape_and_summarize_website,
        CalculatorTool(),
      ]
    return Agent(
        role='本地资深向导',
        goal='为所选城市提供最优洞见与建议',
        backstory="""经验丰富的本地向导，熟知城市景点与风俗文化""",
        tools=tools,
        llm=llm,
        verbose=True)

  # 用于为城市制定精彩行程的agent
  def travel_concierge(self):
    tools: list[BaseTool] = [CalculatorTool()]
    if ENABLE_SEARCH_CONCIERGE:
      tools = [
        SearchTools.search_tool(),
        BrowserTools.scrape_and_summarize_website,
        CalculatorTool(),
      ]
    return Agent(
        role='卓越旅行专家',
        goal="""为该城市制定精彩行程，附预算与行李打包建议""",
        backstory="""深耕旅行规划与出行物流，多年专业经验""",
        tools=tools,
        llm=llm,
        verbose=True)
