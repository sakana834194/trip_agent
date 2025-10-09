from crewai import Crew
from textwrap import dedent
from agents.trip_agents import TripAgents
from agents.trip_tasks import TripTasks

from dotenv import load_dotenv
load_dotenv()

# 旅游规划助手的启动
class TripCrew:

  # 构建城市选择，目的地，兴趣，日期范围
  def __init__(self, origin, cities, date_range, interests):
    self.cities = cities
    self.origin = origin
    self.interests = interests
    self.date_range = date_range

  # 实例化agents与任务
  def run(self):
    agents = TripAgents()
    tasks = TripTasks()

    # 实例化三个agent
    city_selector_agent = agents.city_selection_agent()
    local_expert_agent = agents.local_expert()
    travel_concierge_agent = agents.travel_concierge()

    # 对目的城市进行评估后的任务，规划出目的城市的信息（天气，机票，酒店，景点）
    identify_task = tasks.identify_task(
      city_selector_agent,
      self.origin,
      self.cities,
      self.interests,
      self.date_range
    )

    # 对目标城市的更详细的规划任务，主要包含当地城市的一些风俗文化，打卡地标和其中的必要开销
    gather_task = tasks.gather_task(
      local_expert_agent,
      self.origin,
      self.interests,
      self.date_range
    )

    # 将上述的规划详细整理，制定出完整的行程规划，包含整个旅程的全流程，最终提供格式化输出（markdown）
    plan_task = tasks.plan_task(
      travel_concierge_agent, 
      self.origin,
      self.interests,
      self.date_range
    )

    # 实例化crew，并执行任务
    crew = Crew(
      agents=[
        city_selector_agent, local_expert_agent, travel_concierge_agent
      ],
      tasks=[identify_task, gather_task, plan_task],
      verbose=True
    )

    result = crew.kickoff()
    return result

if __name__ == "__main__":
  print("## 欢迎使用旅游规划助手")
  print('-------------------------------')
  location = input(
    dedent("""
      请问您的出发地是哪里？
    """))
  cities = input(
    dedent("""
      您感兴趣的候选城市有哪些？（可用逗号分隔）
    """))
  date_range = input(
    dedent("""
      您计划出行的日期范围是？（例如 2025-10-01 ~ 2025-10-07）
    """))
  interests = input(
    dedent("""
      您的主要兴趣/偏好是什么？（例如 美食, 博物馆, 漫步）
    """))
  
  trip_crew = TripCrew(location, cities, date_range, interests)

  # 生成最终行程规划
  result = trip_crew.run()
  print("\n\n########################")
  print("## 这是为您生成的行程规划")
  print("########################\n")
  print(result)
