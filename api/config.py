from __future__ import annotations

# 数据库配置
# 使用你的数据库信息：用户名 root / 密码 root / 主机 127.0.0.1:3306 / 数据库 trip_agent
# 驱动：PyMySQL，字符集：utf8mb4
DB_URL: str = "mysql+pymysql://root:root@127.0.0.1:3306/trip_agent?charset=utf8mb4"

# 前端直连后端地址
API_BASE_URL: str = "http://127.0.0.1:9000"

# --- 搜索/联网配置（可调） ---
# 是否启用各 Agent 的 Serper 搜索
ENABLE_SEARCH_CITY_SELECTION: bool = True
ENABLE_SEARCH_LOCAL_EXPERT: bool = True
ENABLE_SEARCH_CONCIERGE: bool = False

# Serper 调用限流/超时参数
SERPER_MAX_CALLS: int = 5         # 每次任务最多调用次数
SERPER_TIMEOUT: int = 12          # 单次调用超时（秒）
SERPER_MIN_INTERVAL: float = 1.0  # 相邻调用最小间隔（秒）
