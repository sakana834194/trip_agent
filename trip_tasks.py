from crewai import Task
from textwrap import dedent
from datetime import date

# 多任务定义
class TripTasks:

    # 用于评估多个目的地后最终作出抉择的任务
    def identify_task(self, agent, origin, cities, interests, range):
        return Task(
            description=dedent(f"""
                请根据天气趋势、季节性活动与旅行成本等具体标准，
                分析并选出本次旅行的最佳城市。该任务需要在多个城市之间进行比较，
                重点考虑当前天气状况、即将到来的文化或季节性活动以及整体出行费用。

                最终产出必须是一份关于所选城市的详细报告，
                包含你的全部发现：实际机票/交通费用、天气预报以及必去景点。
                {self.__tip_section()}

                出发地：{origin}
                候选城市：{cities}
                出行日期：{range}
                旅行兴趣：{interests}
            """),
            agent=agent,
            expected_output="关于所选城市的详细报告，包含交通费用、天气预报与景点推荐"
        )

    # 用于为城市制定精彩行程的任务
    def gather_task(self, agent, origin, interests, range):
        return Task(
            description=dedent(f"""
                作为该城市的本地专家，请为即将到访且追求“极致体验”的旅行者编写一份深度城市指南。
                收集该城市的重点景点、当地风俗、特色活动以及每日行程建议；
                挖掘那些“只有当地人才知道的好去处”。
                指南需全面展示城市亮点，包括小众宝藏、文化热点、必打卡地标、天气预报与大致花费。

                最终结果必须是一份全面的城市指南，
                富含文化洞见与实用提示，旨在显著提升旅行体验。
                {self.__tip_section()}

                出行日期：{range}
                出发地：{origin}
                旅行兴趣：{interests}
            """),
            agent=agent,
            expected_output="全面的城市指南，涵盖小众宝藏、文化热点与实用出行建议"
        )

    # 用于最终行程计划的安排的任务
    def plan_task(self, agent, origin, interests, range):
        return Task(
            description=dedent(f"""
                将上述指南扩展为完整的行程安排，包含每日详细计划、
                天气预报、用餐推荐、行李准备建议与预算拆分。

                请务必提供“真实可去”的景点、“真实可住”的酒店与“真实可吃”的餐厅。

                行程应覆盖从到达到离开的全流程，把城市指南中的信息与实际出行物流整合在一起。

                最终结果必须是一份完整的 Markdown 行程规划，包含：每日时间表、
                预期天气、推荐服装与打包清单，以及详细预算，确保“本次旅行无与伦比”。
                请具体说明选择每个地点的理由与特别之处！{self.__tip_section()}

                出行日期：{range}
                出发地：{origin}
                旅行兴趣：{interests}
            """),
            agent=agent,
            expected_output="完整扩展的旅行计划，含每日安排、天气、行李建议与预算明细"
        )

    def __tip_section(self):
        return "如果你拿出最好的表现，我会给你好评！"
