from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .db import get_db, init_db, User, Plan, PlanVersion, Favorite
from .auth import hash_password, verify_password, create_access_token, get_current_user


router = APIRouter(prefix="/api/v1", tags=["TripPlanner"])


class RegisterReq(BaseModel):
    username: str
    password: str


class LoginReq(BaseModel):
    username: str
    password: str


class TokenResp(BaseModel):
    token: str


@router.on_event("startup")
def _startup():
    init_db()


@router.post("/auth/register", response_model=TokenResp)
def register(req: RegisterReq, db: Session = Depends(get_db)):
    exists = db.scalar(select(func.count()).select_from(User).where(User.username == req.username))
    if exists and int(exists) > 0:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=req.username, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResp(token=create_access_token(user.id, user.username))


@router.post("/auth/login", response_model=TokenResp)
def login(req: LoginReq, db: Session = Depends(get_db)):
    user: User | None = db.scalar(select(User).where(User.username == req.username))
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return TokenResp(token=create_access_token(user.id, user.username))


class SavePlanReq(BaseModel):
    title: str
    data: Dict[str, Any]
    notes: Optional[str] = None
    rating: Optional[int] = None


class SavePlanResp(BaseModel):
    plan_id: int
    version: int


@router.post("/plans/save", response_model=SavePlanResp)
def save_plan(
    req: SavePlanReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.scalar(select(Plan).where(Plan.user_id == user.id, Plan.title == req.title))
    if plan is None:
        plan = Plan(user_id=user.id, title=req.title)
        db.add(plan)
        db.commit()
        db.refresh(plan)

    current_max: int | None = db.scalar(select(func.max(PlanVersion.version)).where(PlanVersion.plan_id == plan.id))
    next_ver = (current_max or 0) + 1
    ver = PlanVersion(plan_id=plan.id, version=next_ver, data=req.data, notes=req.notes, rating=req.rating)
    db.add(ver)
    db.commit()
    return SavePlanResp(plan_id=plan.id, version=next_ver)


class PlanBrief(BaseModel):
    id: int
    title: str
    latest_version: int


@router.get("/plans", response_model=List[PlanBrief])
def list_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Plan.id, Plan.title, func.max(PlanVersion.version))
        .join(PlanVersion, Plan.id == PlanVersion.plan_id)
        .where(Plan.user_id == user.id)
        .group_by(Plan.id, Plan.title)
        .order_by(func.max(PlanVersion.version).desc())
    ).all()
    return [PlanBrief(id=r[0], title=r[1], latest_version=int(r[2] or 1)) for r in rows]


class PlanVersionResp(BaseModel):
    id: int
    version: int
    data: Dict[str, Any]
    notes: Optional[str] = None
    rating: Optional[int] = None


@router.get("/plans/{plan_id}/versions", response_model=List[PlanVersionResp])
def list_versions(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail="计划不存在")
    versions = db.execute(select(PlanVersion).where(PlanVersion.plan_id == plan_id).order_by(PlanVersion.version.desc())).scalars().all()
    return [
        PlanVersionResp(id=v.id, version=v.version, data=v.data, notes=v.notes, rating=v.rating)
        for v in versions
    ]


@router.post("/plans/{plan_id}/favorite")
def toggle_favorite(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail="计划不存在")
    fav = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.plan_id == plan_id))
    if fav is None:
        fav = Favorite(user_id=user.id, plan_id=plan_id, active=True)
        db.add(fav)
    else:
        fav.active = not bool(fav.active)
    db.commit()
    return {"active": bool(fav.active)}


class ReplanReq(BaseModel):
    plan_id: int
    version: int
    feedback: str


@router.post("/plans/replan", response_model=SavePlanResp)
def replan(req: ReplanReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ver = db.get(PlanVersion, req.version)
    if not ver:
        raise HTTPException(status_code=404, detail="版本不存在")
    plan = db.get(Plan, ver.plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权限")

    # 这里复用之前存储的结构化输入，结合反馈生成新版本（占位实现）
    new_data = dict(ver.data)
    new_data["feedback"] = req.feedback

    current_max: int | None = db.scalar(select(func.max(PlanVersion.version)).where(PlanVersion.plan_id == plan.id))
    next_ver = (current_max or 0) + 1
    nv = PlanVersion(plan_id=plan.id, version=next_ver, data=new_data)
    db.add(nv)
    db.commit()
    return SavePlanResp(plan_id=plan.id, version=next_ver)


# 地理编码与路线规划（占位：由前端提交站点与模式，后端返回路径序列）
class RouteReq(BaseModel):
    points: List[Dict[str, float]]  # [{lat, lng}]
    mode: str  # walking, driving, transit


class RouteResp(BaseModel):
    distance_km: float
    duration_min: float
    path: List[Dict[str, float]]


@router.post("/route", response_model=RouteResp)
def compute_route(req: RouteReq):
    # 简化：直接返回原路径，附上粗略里程/时间估算
    n = max(1, len(req.points) - 1)
    base_speed = {"walking": 4.5, "driving": 40.0, "transit": 25.0}.get(req.mode, 5.0)  # km/h
    # 以 2km/段 粗略估计
    distance_km = 2.0 * n
    duration_min = distance_km / base_speed * 60.0
    return RouteResp(distance_km=distance_km, duration_min=duration_min, path=req.points)


