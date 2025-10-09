from crewai_tools import SerperDevTool


class SearchTools():

  @staticmethod
  # 使用内置的serper工具
  def search_tool():
    return SerperDevTool()
