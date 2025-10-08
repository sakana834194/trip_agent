from crewai import Crew
from textwrap import dedent
from agents.trip_agents import TripAgents
from agents.trip_tasks import TripTasks

from dotenv import load_dotenv
load_dotenv()

class TripCrew:

  def __init__(self, origin, cities, date_range, interests):
    self.cities = cities
    self.origin = origin
    self.interests = interests
    self.date_range = date_range

  def run(self):
    agents = TripAgents()
    tasks = TripTasks()

    city_selector_agent = agents.city_selection_agent()
    local_expert_agent = agents.local_expert()
    travel_concierge_agent = agents.travel_concierge()

    identify_task = tasks.identify_task(
      city_selector_agent,
      self.origin,
      self.cities,
      self.interests,
      self.date_range
    )
    gather_task = tasks.gather_task(
      local_expert_agent,
      self.origin,
      self.interests,
      self.date_range
    )
    plan_task = tasks.plan_task(
      travel_concierge_agent, 
      self.origin,
      self.interests,
      self.date_range
    )

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
  result = trip_crew.run()
  print("\n\n########################")
  print("## 这是为您生成的行程规划")
  print("########################\n")
  print(result)
