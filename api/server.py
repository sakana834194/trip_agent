from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from agents.main import TripCrew
import datetime as dt
from .routes import router as api_router
import concurrent.futures
import time

# 创建计划请求
class PlanRequest(BaseModel):
  origin: str
  cities: str  # 逗号分隔的候选城市
  date_range: str  # 形如 "2025-10-01 ~ 2025-10-07"
  interests: str | None = None

# 创建每日行程响应
class DayPlan(BaseModel):
  date: str
  activities: List[str]
  meals: List[str] | None = None
  notes: str | None = None

# 创建计划响应
class PlanResponse(BaseModel):
  summary: str
  days: List[DayPlan]
  budget_estimate: Dict[str, Any] | None = None
  raw_markdown: str

# 创建FastAPI应用
app = FastAPI(title="Trip Planner API", version="1.0.0")
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(api_router)

# 解析日期范围
def parse_date_range(date_range: str) -> List[str]:
  # 兼容多种分隔与格式：优先正则提取 YYYY-MM-DD
  import re
  try:
    found = re.findall(r"(\d{4}-\d{1,2}-\d{1,2})", date_range)
    dates: List[dt.date] = []
    for s in found[:2]:
      dates.append(dt.datetime.strptime(s, "%Y-%m-%d").date())
    if len(dates) == 2:
      start, end = sorted(dates)
    elif len(dates) == 1:
      start = end = dates[0]
    else:
      # 回退：尝试按常见分隔符分割
      for sep in ["~", "～", "-", "—", "至", "到"]:
        if sep in date_range:
          parts = [p.strip() for p in date_range.split(sep) if p.strip()]
          if len(parts) >= 1:
            start = dt.datetime.strptime(parts[0], "%Y-%m-%d").date()
            end = start if len(parts) == 1 else dt.datetime.strptime(parts[1], "%Y-%m-%d").date()
            break
      else:
        # 彻底失败：使用当天
        start = end = dt.date.today()

    days = []
    cur = start
    while cur <= end:
      days.append(cur.isoformat())
      cur += dt.timedelta(days=1)
    return days
  except Exception:
    # 最后兜底：当天
    return [dt.date.today().isoformat()]

# 将markdown文本转换为结构化数据
def naive_markdown_to_struct(md_text: str, days: List[str]) -> PlanResponse:
  # 简易解析：按日期标题或行分割，不保证完美，但可提供结构化导出
  days = days or [dt.date.today().isoformat()]
  day_blocks: Dict[str, List[str]] = {d: [] for d in days}
  active_day: str | None = None
  for line in md_text.splitlines():
    t = line.strip()
    if t.startswith("#") or t.startswith("##") or t.startswith("###"):
      for d in days:
        if d in t:
          active_day = d
          break
      continue
    if active_day and t:
      day_blocks[active_day].append(t)

  day_plans: List[DayPlan] = []
  for d in days:
    items = [s for s in day_blocks.get(d, []) if s]
    day_plans.append(DayPlan(date=d, activities=items[:10]))

  summary = f"行程共 {len(days)} 天；出发至返回全流程涵盖交通、餐饮与景点。"
  return PlanResponse(summary=summary, days=day_plans, budget_estimate=None, raw_markdown=md_text)

# 创建计划
@app.post("/api/v1/plan", response_model=PlanResponse)
def create_plan(req: PlanRequest):
  if not req.origin or not req.cities or not req.date_range:
    raise HTTPException(status_code=400, detail="缺少必要参数")
  crew = TripCrew(req.origin, req.cities, req.date_range, req.interests or "")
  # 增加超时保护，避免前端长时间等待（默认 180s）
  try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
      future = executor.submit(crew.run)
      result = future.result(timeout=180)
  except concurrent.futures.TimeoutError:
    raise HTTPException(status_code=504, detail="规划超时，请稍后重试或减少联网搜索")
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"规划失败: {type(e).__name__}: {e}")

  md_text = str(result)
  days = parse_date_range(req.date_range)
  return naive_markdown_to_struct(md_text, days)

# 创建计划ICS
@app.post("/api/v1/plan/ics")
def create_plan_ics(req: PlanRequest):
  if not req.origin or not req.cities or not req.date_range:
    raise HTTPException(status_code=400, detail="缺少必要参数")
  # ICS 仅按日期生成占位；不重复进行昂贵的规划
  md_text = "生成 ICS 占位：如需内容，请先调用 /api/v1/plan 获取 Markdown"
  days = parse_date_range(req.date_range)
  # 生成极简 ICS，按天占位
  ics_lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//TripPlanner//CN",
  ]
  for d in days:
    ics_lines += [
      "BEGIN:VEVENT",
      f"DTSTAMP:{d.replace('-', '')}T090000Z",
      f"DTSTART;VALUE=DATE:{d.replace('-', '')}",
      f"SUMMARY:旅行日程 {d}",
      "END:VEVENT",
    ]
  ics_lines.append("END:VCALENDAR")
  return {"ics": "\r\n".join(ics_lines), "raw_markdown": md_text}


