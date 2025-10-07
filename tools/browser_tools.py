import json
import os

import requests
from crewai.tools import BaseTool
from unstructured.partition.html import partition_html


class ScrapeWebsiteTool(BaseTool):
  name: str = "抓取网站内容"
  description: str = (
    "抓取并返回网页主要文本内容；优先使用 Browserless，缺省回退为直接抓取。"
  )

  def _run(self, website: str) -> str:
    api_key = os.environ.get('BROWSERLESS_API_KEY')
    try:
      if api_key:
        url = f"https://chrome.browserless.io/content?token={api_key}"
        payload = json.dumps({"url": website})
        headers = {'cache-control': 'no-cache', 'content-type': 'application/json'}
        response = requests.request("POST", url, headers=headers, data=payload, timeout=60)
        response.raise_for_status()
        html = response.text
      else:
        headers = {
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        response = requests.get(website, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text

      elements = partition_html(text=html)
      content = "\n\n".join([str(el) for el in elements])
      if len(content) > 16000:
        content = content[:16000]
      return content
    except Exception as e:
      return f"[BrowserTools] 抓取失败: {type(e).__name__}: {e}"


class BrowserTools():
  # 暴露与原用法兼容的工具实例
  scrape_and_summarize_website = ScrapeWebsiteTool()
