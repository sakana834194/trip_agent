from crewai_tools import SerperDevTool


class SearchTools():

  @staticmethod
  def search_tool():
    return SerperDevTool()
