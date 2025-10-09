from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

# 导入jwt库，用于生成和验证JWT token
import jwt 
# 导入fastapi库，用于依赖注入和HTTP异常处理
from fastapi import Depends, HTTPException, status 
# 导入fastapi安全库，用于认证
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
# 导入passlib库，用于密码加密和验证
from passlib.context import CryptContext 
# 导入sqlalchemy库，用于数据库操作
from sqlalchemy.orm import Session 

# 导入db库，用于数据库操作
from .db import User, get_db

# 安全认证，如有需要可自行配置
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

# 使用 PBKDF2-SHA256 以避免 bcrypt 在部分环境的兼容问题与 72 字节限制
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# 密码加密
def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)

# 密码验证
def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)

# 创建访问令牌
def create_access_token(user_id: int, username: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

# 获取当前用户
def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    if creds is None or not creds.scheme.lower().startswith("bearer"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = int(payload.get("sub", "0"))
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")


