import streamlit as st
import requests
import json
import base64
import datetime as dt
import os
from config import API_BASE_URL
from dotenv import load_dotenv
from typing import Any

# 可选的 Lottie 动画支持
try:
    from streamlit_lottie import st_lottie  
except Exception:
    st_lottie = None

# 地图可视化支持
try:
    from streamlit_folium import st_folium  # type: ignore
    import folium  # type: ignore
except Exception:
    st_folium = None
    folium = None

# 轻量地理编码
try:
    from geopy.geocoders import Nominatim  # type: ignore
    from geopy.extra.rate_limiter import RateLimiter  # type: ignore
except Exception:
    Nominatim = None
    RateLimiter = None

# 使用 geonamescache 提供的国家/城市数据库
try:
    import geonamescache  # type: ignore
    GC = geonamescache.GeonamesCache()
    _countries = GC.get_countries()
    HOT_COUNTRIES = {'CN': '中国', 'JP': '日本', 'KR': '韩国', 'US': '美国', 'GB': '英国', 'RU': '俄罗斯'}
    COUNTRY_CODE_TO_NAME = {code: HOT_COUNTRIES.get(code, data['name']) for code, data in _countries.items() if code in HOT_COUNTRIES}
    COUNTRY_CHOICES = [COUNTRY_CODE_TO_NAME[c] for c in COUNTRY_CODE_TO_NAME]
    NAME_TO_CODE = {v: k for k, v in COUNTRY_CODE_TO_NAME.items()}
    _cities = GC.get_cities()
    CITIES_BY_COUNTRY = {}
    for _, cdata in _cities.items():
        cc = cdata.get('countrycode')
        name = cdata.get('name')
        if cc in COUNTRY_CODE_TO_NAME and name:
            CITIES_BY_COUNTRY.setdefault(cc, set()).add(name)
    for cc in list(CITIES_BY_COUNTRY.keys()):
        CITIES_BY_COUNTRY[cc] = sorted(CITIES_BY_COUNTRY[cc])
except Exception:
    geonamescache = None
    GC = None
    COUNTRY_CHOICES = ["中国", "日本", "韩国", "美国", "英国", "俄罗斯"]
    NAME_TO_CODE = {"中国":"CN","日本":"JP","韩国":"KR","美国":"US","英国":"GB","俄罗斯":"RU"}
    CITIES_BY_COUNTRY = {k: [] for k in NAME_TO_CODE.values()}

# 热门国家中文城市（离线），可扩展
CHINESE_CITIES = {
    "中国": ["北京", "上海", "广州", "深圳", "成都", "杭州", "西安", "重庆", "武汉", "苏州"],
    "日本": ["东京", "大阪", "京都", "札幌", "名古屋", "福冈"],
    "韩国": ["首尔", "釜山", "济州", "仁川"],
    "美国": ["纽约", "洛杉矶", "旧金山", "拉斯维加斯", "华盛顿", "西雅图", "芝加哥"],
    "英国": ["伦敦", "曼彻斯特", "利物浦", "爱丁堡", "格拉斯哥"],
    "俄罗斯": ["莫斯科", "圣彼得堡", "海参崴"],
}

# 高德中国行政区层级（在线）
@st.cache_data(ttl=86400)
def fetch_amap_china_hierarchy(api_key: str) -> tuple[list[str], dict[str, list[str]]]:
    import requests
    url = "https://restapi.amap.com/v3/config/district"
    params = {
        "keywords": "中国",
        "subdistrict": 2,  # 返回省->市
        "extensions": "base",
        "key": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        provinces: list[str] = []
        cities_by_province: dict[str, list[str]] = {}
        for country in data.get("districts", []):
            for province in country.get("districts", []):
                pname = province.get("name")
                if not pname:
                    continue
                provinces.append(pname)
                plist: list[str] = []
                for city in province.get("districts", []):
                    cname = city.get("name")
                    if cname:
                        plist.append(cname)
                cities_by_province[pname] = sorted(list(set(plist)))
        return sorted(list(set(provinces))), cities_by_province
    except Exception:
        return [], {}

def fetch_amap_china_cities(api_key: str) -> list[str]:
    # 基于省份->城市层级，汇总为去重后的全国市级名单
    provinces, cities_by_province = fetch_amap_china_hierarchy(api_key)
    unique_cities: set[str] = set()
    for prov in provinces:
        for cname in cities_by_province.get(prov, []):
            if cname:
                unique_cities.add(cname)
    return sorted(unique_cities)

def get_amap_key() -> str:
    # 优先 AMAP_KEY，其次 AMAP_APIKEY
    return os.getenv("AMAP_KEY")  or os.getenv("AMAP_APIKEY") or ""


load_dotenv()
st.set_page_config(page_title="旅游规划助手", page_icon="🧭", layout="wide")

custom_css = """
<style>
/* 加载字体：Inter + Noto Sans SC（中文） */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

.stApp {  
  background: linear-gradient(135deg, #E6F2FF 0%, #F7FBFF 100%);
  font-family: 'Inter', 'Noto Sans SC', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji';
}

/* 使内容居中且更窄 */
.block-container {max-width: 1100px; margin: 0 auto;}

/* 居中标题 */
.title-center { text-align: center; }

/* 表单容器居中显示 */
.form-card { 
  background: rgba(255,255,255,.96);
  padding: 1.2rem 1.4rem; 
  border-radius: 14px; 
  border: 1px solid rgba(30,64,175,.18);
  box-shadow: 0 8px 24px rgba(30,64,175,.10);
}

/* 按钮样式与动效 */
.stButton>button {
  background: #2563EB;
  border: none;
  color: #fff;
  border-radius: 10px;
  padding: 0.6rem 1.2rem;
  transition: transform 0.08s ease, box-shadow 0.2s ease;
  box-shadow: 0 6px 18px rgba(37,99,235,.25);
}
.stButton>button:hover {transform: translateY(-1px);} 
.stButton>button:active {transform: translateY(0);} 

/* 结果卡片 */
.result-card {background: rgba(255,255,255,.95); padding: 1.2rem 1.4rem; border-radius: 12px; border: 1px solid rgba(30,64,175,.12);} 

/* 防止非输入区域出现光标 */
*::selection { background: rgba(37,99,235,.18); }
div, p, h1, h2, h3, h4, h5, h6 { caret-color: transparent; }
input, textarea { caret-color: auto; }

/* 让上方联动选择更醒目且更宽，按钮同行靠右 */
div[data-testid="stSelectbox"] { width: 100%; }
div[data-testid="stSelectbox"] > div { border: 1px solid rgba(37,99,235,.35); border-radius: 10px; }
.inline-row { padding: .25rem 0; display: flex; justify-content: flex-end; align-items: flex-end; }
.inline-row .stButton>button {
  display: inline-flex;
  align-items: center;
  height: 44px;            /* 与选择框高度保持一致 */
  line-height: 44px;
  padding: 0 14px;         /* 横向内边距 */
  white-space: nowrap;     /* 阻止“添加”换行 */
  writing-mode: horizontal-tb; /* 横向文字方向 */
  margin-top: 0;           /* 交由父容器对齐 */
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

st.markdown("<h1 class='title-center'>旅游规划助手 🧭</h1>", unsafe_allow_html=True)
st.markdown("<p class='title-center' style='opacity:.8'>填写出发地、候选城市、日期范围与兴趣偏好，生成行程规划。</p>", unsafe_allow_html=True)



# 初始化会话状态
if "origin_input" not in st.session_state:
    st.session_state["origin_input"] = ""
if "cities_input" not in st.session_state:
    st.session_state["cities_input"] = ""
if "country_o_sel" not in st.session_state:
    st.session_state["country_o_sel"] = "请选择"
if "country_c_sel" not in st.session_state:
    st.session_state["country_c_sel"] = "请选择"

# 登录/用户态
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = ""
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "plan_data" not in st.session_state:
    st.session_state["plan_data"] = None  # 保存后端结构化结果
if "map_state" not in st.session_state:
    st.session_state["map_state"] = {"mode_per_day": {}, "stops_by_day": {}}  # {date: [{name,lat,lng}]}
if "_last_origin" not in st.session_state:
    st.session_state["_last_origin"] = ""
if "_last_cities" not in st.session_state:
    st.session_state["_last_cities"] = ""

with st.sidebar:
    st.markdown("### 个人空间")
    api_base = API_BASE_URL
    if not st.session_state.get("auth_token"):
        tab_login, tab_reg = st.tabs(["登录", "注册"])
        with tab_login:
            u = st.text_input("用户名", key="_login_u")
            p = st.text_input("密码", type="password", key="_login_p")
            if st.button("登录"):
                try:
                    r = requests.post(f"{api_base}/api/v1/auth/login", json={"username": u, "password": p}, timeout=20)
                    r.raise_for_status()
                    token = r.json().get("token", "")
                    if token:
                        st.session_state["auth_token"] = token
                        st.session_state["username"] = u
                        st.success("登录成功")
                except Exception as e:
                    st.error(f"登录失败：{e}")
        with tab_reg:
            ru = st.text_input("用户名", key="_reg_u")
            rp = st.text_input("密码", type="password", key="_reg_p")
            if st.button("注册并登录"):
                try:
                    r = requests.post(f"{api_base}/api/v1/auth/register", json={"username": ru, "password": rp}, timeout=20)
                    r.raise_for_status()
                    token = r.json().get("token", "")
                    if token:
                        st.session_state["auth_token"] = token
                        st.session_state["username"] = ru
                        st.success("注册成功")
                except Exception as e:
                    st.error(f"注册失败：{e}")
    else:
        st.write(f"已登录：{st.session_state['username']}")
        if st.button("退出登录"):
            st.session_state["auth_token"] = ""
            st.session_state["username"] = ""
        st.divider()
        # 我的计划
        if st.button("刷新我的计划"):
            try:
                resp = requests.get(f"{api_base}/api/v1/plans", headers={"Authorization": f"Bearer {st.session_state['auth_token']}"}, timeout=20)
                st.session_state["_my_plans"] = resp.json()
            except Exception as e:
                st.error(f"获取计划失败：{e}")
        plans = st.session_state.get("_my_plans", [])
        if plans:
            plan_labels = [f"#{p['id']} - {p['title']} (v{p['latest_version']})" for p in plans]
            idx = st.selectbox("选择计划", list(range(len(plans))), format_func=lambda i: plan_labels[i])
            pid = plans[idx]["id"]
            if st.button("查看版本"):
                try:
                    r = requests.get(f"{api_base}/api/v1/plans/{pid}/versions", headers={"Authorization": f"Bearer {st.session_state['auth_token']}"}, timeout=20)
                    st.session_state["_plan_versions"] = r.json()
                    st.session_state["_active_plan_id"] = pid
                except Exception as e:
                    st.error(f"获取版本失败：{e}")
        vers = st.session_state.get("_plan_versions", [])
        if vers:
            vidx = st.selectbox("选择版本", list(range(len(vers))), format_func=lambda i: f"v{vers[i]['version']}#{vers[i]['id']}")
            if st.button("设为当前"):
                v = vers[vidx]
                st.session_state["plan_data"] = v["data"]
                st.info("已加载所选版本为当前行程。")
            if st.button("收藏/取消收藏"):
                try:
                    pid = st.session_state.get("_active_plan_id")
                    if pid:
                        r = requests.post(f"{api_base}/api/v1/plans/{pid}/favorite", headers={"Authorization": f"Bearer {st.session_state['auth_token']}"}, timeout=20)
                        st.toast("已切换收藏状态")
                except Exception:
                    st.error("操作失败")
            st.markdown("**批注与评分**")
            fb = st.text_area("批注/再规划需求", key="_replan_fb")
            score = st.slider("评分", 1, 5, 5)
            if st.button("一键再规划"):
                try:
                    v = vers[vidx]
                    payload = {"plan_id": st.session_state.get("_active_plan_id"), "version": v["id"], "feedback": f"评分: {score}; {fb}"}
                    r = requests.post(f"{api_base}/api/v1/plans/replan", json=payload, headers={"Authorization": f"Bearer {st.session_state['auth_token']}"}, timeout=60)
                    r.raise_for_status()
                    st.success("已创建新版本，刷新我的计划查看。")
                except Exception as e:
                    st.error(f"再规划失败：{e}")

with st.container():
    # 出发地：国家 →（中国：省份）→ 城市 或手动输入（联动刷新）
    st.markdown("**出发地（国家 → 省份 → 城市 或 手动输入）**")
    COUNTRY_UI = ["请选择", "手动输入"] + COUNTRY_CHOICES
    col1, col2, col3 = st.columns([2,2,4], gap="small")
    with col1:
        country_o_sel = st.selectbox("国家", COUNTRY_UI, index=COUNTRY_UI.index(st.session_state["country_o_sel"]) if st.session_state.get("country_o_sel") in COUNTRY_UI else 0, key="country_o_sel")
    with col2:
        # 对中国：合并热门城市 + 省份列表；其他国家：城市列表
        selector_label = "城市"
        combined_options: list[str] = ["请选择", "手动输入"]
        province_o_sel = ""
        city_o_sel = ""
        if country_o_sel == "手动输入":
            st.text_input("国家_手动", key="country_o_sel_manual")
            city_o_sel = st.text_input("城市_手动", key="city_o_sel_manual")
        elif country_o_sel == "中国":
            selector_label = "热门城市 / 省份"
            amap_key = get_amap_key()
            provinces: list[str] = []
            if amap_key:
                provinces, cities_map = fetch_amap_china_hierarchy(amap_key)
                st.session_state["_amap_cities_by_prov"] = cities_map
            hot = CHINESE_CITIES.get("中国", [])
            combined_options = ["请选择", "手动输入"] + hot + provinces
            first_sel = st.selectbox(selector_label, combined_options, index=0, key="cn_first_selector_o")
            if first_sel == "手动输入":
                city_o_sel = st.text_input("城市_手动", key="city_o_sel_manual")
            elif first_sel in provinces:
                province_o_sel = first_sel
                prov_cities = st.session_state.get("_amap_cities_by_prov", {}).get(province_o_sel, [])
                st.session_state["_origin_city_mode"] = "province"
                st.session_state["_origin_prov_cities_opts"] = ["请选择", "手动输入"] + prov_cities
            elif first_sel in hot:
                city_o_sel = first_sel
            else:
                city_o_sel = ""
        elif country_o_sel != "请选择":
            zh_cities = CHINESE_CITIES.get(country_o_sel)
            options = ["请选择", "手动输入"] + (zh_cities if zh_cities else CITIES_BY_COUNTRY.get(NAME_TO_CODE.get(country_o_sel, ""), []))
            city_o_sel = st.selectbox("城市", options, index=0, key="city_o_sel")
            if city_o_sel == "手动输入":
                city_o_sel = st.text_input("城市_手动", key="city_o_sel_manual")
        # 保存当前选择到 session，供按钮使用
        st.session_state["_origin_country"] = country_o_sel
        st.session_state["_origin_province"] = province_o_sel
        st.session_state["_origin_city"] = city_o_sel
    with col3:
        # 将城市下拉与添加按钮放在同一行的子列中，保证不换行
        sub_city, sub_btn = st.columns([5,1], gap="small")
        with sub_city:
            city_final = st.session_state.get("_origin_city", "")
            if country_o_sel == "中国" and st.session_state.get("_origin_city_mode") == "province":
                opts = st.session_state.get("_origin_prov_cities_opts", ["请选择", "手动输入"])
                city_sel = st.selectbox("城市", opts, index=0, key="city_o_sel_cn")
                if city_sel == "手动输入":
                    city_sel = st.text_input("城市_手动", key="city_o_sel_manual")
                city_final = city_sel
                st.session_state["_origin_city"] = city_final
        with sub_btn:
            st.markdown("<div class='inline-row'>", unsafe_allow_html=True)
            if st.button("添加", key="add_origin_inline_btn"):
                oc = st.session_state.get("_origin_country", "")
                op = st.session_state.get("_origin_province", "")
                oy = st.session_state.get("_origin_city", "")
                st.session_state["origin_input"] = "-".join([s for s in [oc, op, oy] if s]).strip("-")
            st.markdown("</div>", unsafe_allow_html=True)

    # 候选城市：国家 →（中国：省份）→ 城市 或手动输入
    st.markdown("**候选城市（国家 → 省份 → 城市 或 手动输入）**")
    COUNTRY_UI_C = ["请选择", "手动输入"] + COUNTRY_CHOICES
    col4, col5, col6 = st.columns([2,2,4], gap="small")
    with col4:
        country_c_sel = st.selectbox("国家_候选", COUNTRY_UI_C, index=COUNTRY_UI_C.index(st.session_state["country_c_sel"]) if st.session_state.get("country_c_sel") in COUNTRY_UI_C else 0, key="country_c_sel")
    with col5:
        province_c_sel = ""
        city_c_sel = ""
        if country_c_sel == "手动输入":
            st.text_input("国家_候选_手动", key="country_c_manual")
            city_c_sel = st.text_input("城市_候选_手动", key="city_c_manual")
        elif country_c_sel == "中国":
            amap_key_c = get_amap_key()
            provinces_c: list[str] = []
            if amap_key_c:
                provinces_c, cities_map_c = fetch_amap_china_hierarchy(amap_key_c)
                st.session_state["_amap_cities_by_prov_c"] = cities_map_c
            hot_c = CHINESE_CITIES.get("中国", [])
            combined_c = ["请选择", "手动输入"] + hot_c + provinces_c
            first_sel_c = st.selectbox("热门城市 / 省份_候选", combined_c, index=0, key="cn_first_selector_c")
            if first_sel_c == "手动输入":
                city_c_sel = st.text_input("城市_候选_手动", key="city_c_manual")
            elif first_sel_c in provinces_c:
                province_c_sel = first_sel_c
                prov_cities_c = st.session_state.get("_amap_cities_by_prov_c", {}).get(province_c_sel, [])
                st.session_state["_cand_city_mode"] = "province"
                st.session_state["_cand_prov_cities_opts"] = ["请选择", "手动输入"] + prov_cities_c
            elif first_sel_c in hot_c:
                city_c_sel = first_sel_c
            else:
                city_c_sel = ""
        elif country_c_sel != "请选择":
            zh_cities_c = CHINESE_CITIES.get(country_c_sel)
            options_c = ["请选择", "手动输入"] + (zh_cities_c if zh_cities_c else CITIES_BY_COUNTRY.get(NAME_TO_CODE.get(country_c_sel, ""), []))
            city_c_sel = st.selectbox("城市_候选", options_c, index=0, key="city_c_sel_generic")
            if city_c_sel == "手动输入":
                city_c_sel = st.text_input("城市_候选_手动", key="city_c_manual")
        st.session_state["_cand_country"] = country_c_sel
        st.session_state["_cand_province"] = province_c_sel
        st.session_state["_cand_city"] = city_c_sel
    with col6:
        sub_city2, sub_btn2 = st.columns([5,1], gap="small")
        with sub_city2:
            if country_c_sel == "中国" and st.session_state.get("_cand_city_mode") == "province":
                opts_c = st.session_state.get("_cand_prov_cities_opts", ["请选择", "手动输入"])
                city_c_selected = st.selectbox("城市_候选", opts_c, index=0, key="city_c_sel_cn")
                if city_c_selected == "手动输入":
                    city_c_selected = st.text_input("城市_候选_手动", key="city_c_manual")
                st.session_state["_cand_city"] = city_c_selected
        with sub_btn2:
            st.markdown("<div class='inline-row'>", unsafe_allow_html=True)
            if st.button("添加", key="add_city_inline_btn"):
                cc = st.session_state.get("_cand_country", "")
                cp = st.session_state.get("_cand_province", "")
                cy = st.session_state.get("_cand_city", "")
                label = "-".join([s for s in [cc, cp, cy] if s]).strip("-")
                if label:
                    current = [c.strip() for c in st.session_state.get("cities_input", "").split(",") if c.strip()]
                    if label not in current:
                        current.append(label)
                    st.session_state["cities_input"] = ", ".join(current)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with st.container():
    # 表单：仅收集最终文本并在底部统一提供按钮
    with st.form("trip_form", clear_on_submit=False):
        st.text_input("出发地（可手动编辑）", key="origin_input")
        st.text_area("候选城市（逗号分隔，可编辑）", key="cities_input")

        # 3) 日期选择器（区间）
        st.markdown("**出行日期范围**")
        start_default = dt.date.today()
        end_default = start_default + dt.timedelta(days=7)
        _date_pick = st.date_input(
            "选择日期范围",
            value=(start_default, end_default)
        )
        # 兼容单选/区间返回
        if isinstance(_date_pick, tuple) and len(_date_pick) == 2:
            start_date, end_date = _date_pick
        else:
            start_date = _date_pick if hasattr(_date_pick, "__str__") else start_default
            end_date = start_date
        date_range = f"{start_date} ~ {end_date}"

        # 4) 兴趣
        interests = st.text_area("兴趣/偏好（可选）", placeholder="美食, 博物馆, 漫步, 摄影")

        submitted_generate = st.form_submit_button("生成行程 ✨", key="submit_generate_btn")
    st.markdown("</div>", unsafe_allow_html=True)

# 动画：放在表单下方
with st.container():
    # 轻量 Lottie 动画
    try:
        if st_lottie is not None:
            # 使用最小有效 Lottie 结构，避免语法错误
            lottie_json_str = "{""v"":""5.7.4"",""fr"":30,""ip"":0,""op"":60,""w"":200,""h"":200,""nm"":""pulse"",""ddd"":0,""assets"":[],""layers"":[]}"
            lottie = json.loads(lottie_json_str)
            st_lottie(lottie, height=220, speed=1, loop=True, quality="low")
        else:
            st.markdown("<div style='opacity:.8'>✨ 准备好出发了吗？</div>", unsafe_allow_html=True)
    except Exception:
        st.empty()

if 'submitted_generate' in locals() and submitted_generate:
    # 从会话状态读取最终值
    origin = st.session_state.get("origin_input", "")
    cities = st.session_state.get("cities_input", "")
    # 顶部行内“添加”按钮已直接写入 session；此处无需再处理
    if not origin or not cities or not date_range:
        st.warning("请填写至少：出发地、候选城市、日期范围。")
    else:
        api_base = API_BASE_URL
        with st.spinner("旅游行程正在规划中，请稍候..."):
            try:
                payload = {"origin": origin, "cities": cities, "date_range": date_range, "interests": interests}
                resp = requests.post(f"{api_base}/api/v1/plan", json=payload, timeout=300)
                resp.raise_for_status()
                data = resp.json()
                st.success("行程已生成！")
                st.markdown("### 结果（结构化）")
                st.json(data)

                # 存入会话供地图/保存使用
                st.session_state["plan_data"] = data
                st.session_state["_last_origin"] = origin
                st.session_state["_last_cities"] = cities

                # 若已登录则自动保存一个版本，便于后续收藏/版本管理
                if st.session_state.get("auth_token"):
                    try:
                        auto_title = f"{origin} 行程 {date_range}"
                        plan_copy = dict(data)
                        plan_copy.setdefault("meta", {})
                        plan_copy["meta"].update({
                            "origin": origin,
                            "cities": cities,
                            "date_range": date_range,
                            "saved_at": str(dt.datetime.now()),
                        })
                        rsave = requests.post(
                            f"{api_base}/api/v1/plans/save",
                            headers={"Authorization": f"Bearer {st.session_state['auth_token']}"},
                            json={"title": auto_title, "data": plan_copy},
                            timeout=30,
                        )
                        rsave.raise_for_status()
                        st.toast("已自动保存当前行程为新版本")
                    except Exception:
                        st.info("已生成行程，登录后可手动保存为版本")

                # JSON 导出
                json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                b64_json = base64.b64encode(json_bytes).decode()
                st.markdown(f'<a href="data:application/json;base64,{b64_json}" download="trip_plan.json">📥 下载 JSON</a>', unsafe_allow_html=True)

                # ICS 导出
                resp_ics = requests.post(f"{api_base}/api/v1/plan/ics", json=payload, timeout=300)
                resp_ics.raise_for_status()
                ics_data = resp_ics.json().get("ics", "")
                ics_b64 = base64.b64encode(ics_data.encode("utf-8")).decode()
                st.markdown(f'<a href="data:text/calendar;base64,{ics_b64}" download="trip_plan.ics">📅 下载 ICS</a>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"运行失败：{type(e).__name__}: {e}")



# ===== 地图与路线可视化 =====
def geocode_addresses(names: list[str], city_hint: str = "") -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if Nominatim is None:
        return results
    geolocator = Nominatim(user_agent="trip_planner_app")
    geocode_func = getattr(geolocator, "geocode", None)
    if not callable(geocode_func):
        return results
    # RateLimiter 可能不存在；做兼容处理
    if RateLimiter:
        geocode = RateLimiter(geocode_func, min_delay_seconds=1.0)
    else:
        def geocode(q: str):
            return geocode_func(q, timeout=10)
    for name in names:
        query = name
        if city_hint:
            query = f"{city_hint} {name}"
        try:
            loc = geocode(query)
            lat = getattr(loc, "latitude", None) if loc is not None else None
            lng = getattr(loc, "longitude", None) if loc is not None else None
            if lat is not None and lng is not None:
                results.append({"name": name, "lat": float(lat), "lng": float(lng)})
        except Exception:
            continue
    return results


def render_map_and_route(day_key: str, stops: list[dict], mode: str, api_base: str):
    if not st_folium or not folium:
        st.info("地图组件未安装，已跳过可视化。")
        return None
    if not stops:
        st.warning("请先设置至少两个站点。")
        return None

    pts = [{"lat": float(s["lat"]), "lng": float(s["lng"])} for s in stops if "lat" in s and "lng" in s]
    if len(pts) < 2:
        st.warning("至少需要两个有效坐标以计算路线。")
        return None

    # 路线计算
    try:
        r = requests.post(f"{api_base}/api/v1/route", json={"points": pts, "mode": mode}, timeout=20)
        r.raise_for_status()
        route = r.json()
    except Exception as e:
        st.error(f"路线计算失败：{e}")
        return None

    # 地图
    avg_lat = sum(p["lat"] for p in pts) / len(pts)
    avg_lng = sum(p["lng"] for p in pts) / len(pts)
    fmap = folium.Map(location=[avg_lat, avg_lng], zoom_start=13, control_scale=True)
    for i, s in enumerate(stops):
        if "lat" in s and "lng" in s:
            folium.Marker([s["lat"], s["lng"]], tooltip=f"{i+1}. {s.get('name','')}" ).add_to(fmap)
    # 折线
    line = [(p["lat"], p["lng"]) for p in route.get("path", [])]
    if line:
        color = {"walking": "#22c55e", "driving": "#2563eb", "transit": "#9333ea"}.get(mode, "#2563eb")
        folium.PolyLine(line, color=color, weight=5, opacity=0.8).add_to(fmap)
    out = st_folium(fmap, width=900, height=500)
    st.caption(f"估算：{route.get('distance_km', 0):.1f} km / {route.get('duration_min', 0):.0f} 分钟")
    return out


plan = st.session_state.get("plan_data")
if plan:
    st.markdown("### 地图与路线可视化")
    api_base = API_BASE_URL
    days = [d.get("date") for d in plan.get("days", [])]
    if not days:
        st.info("暂无可视化天数")
    else:
        d_idx = st.selectbox("选择日期", list(range(len(days))), format_func=lambda i: days[i])
        day_key = days[d_idx]

        # 站点数据（每个日期独立维护）
        stops_by_day: dict = st.session_state["map_state"].setdefault("stops_by_day", {})
        cur_stops: list[dict] = stops_by_day.get(day_key, [])

        with st.expander("从当日活动尝试自动地理编码", expanded=False):
            raw_items = plan.get("days", [])[d_idx].get("activities", [])
            st.write("将按行作为站点尝试解析（可手动清理后编辑）")
            if st.button("开始地理编码"):
                city_hint = st.session_state.get("_last_cities", "").split(",")[0] if st.session_state.get("_last_cities") else ""
                new_pts = geocode_addresses(raw_items[:10], city_hint=city_hint)
                if new_pts:
                    cur_stops = new_pts
                    stops_by_day[day_key] = cur_stops
                else:
                    st.warning("未解析到坐标，请手动添加。")

        st.markdown("**站点编辑（可增删/修改，序号即路线顺序）**")
        edited = st.data_editor(
            cur_stops or [{"name": "地点1", "lat": None, "lng": None}],
            num_rows="dynamic",
            use_container_width=True,
            key=f"_editor_{day_key}",
            column_config={"name": "名称", "lat": "纬度", "lng": "经度"},
        )
        # 保持
        stops_by_day[day_key] = [
            {"name": (row.get("name") or ""), "lat": row.get("lat"), "lng": row.get("lng")}
            for row in edited if row.get("name")
        ]

        colm1, colm2, colm3 = st.columns([2,2,2])
        with colm1:
            mode = st.session_state["map_state"].setdefault("mode_per_day", {}).get(day_key, "walking")
            mode = st.selectbox("出行模式", ["walking", "transit", "driving"], index=["walking","transit","driving"].index(mode))
            st.session_state["map_state"]["mode_per_day"][day_key] = mode
        with colm2:
            if st.button("计算并绘制路线"):
                st.session_state[f"_route_trigger_{day_key}"] = True
        with colm3:
            title_default = f"{st.session_state.get('_last_origin','出发地')} 行程 {day_key}"
            title = st.text_input("保存标题", value=title_default, key=f"_save_title_{day_key}")
            if st.session_state.get("auth_token") and st.button("保存当前版本"):
                try:
                    # 将地图编辑数据合并回 plan
                    plan_copy = dict(plan)
                    plan_copy.setdefault("map", {})
                    plan_copy["map"].setdefault(day_key, {})
                    plan_copy["map"][day_key]["stops"] = stops_by_day.get(day_key, [])
                    plan_copy["map"][day_key]["mode"] = st.session_state["map_state"]["mode_per_day"].get(day_key, "walking")
                    r = requests.post(
                        f"{api_base}/api/v1/plans/save",
                        headers={"Authorization": f"Bearer {st.session_state['auth_token']}"},
                        json={"title": title, "data": plan_copy},
                        timeout=60,
                    )
                    r.raise_for_status()
                    st.success("已保存新版本")
                except Exception as e:
                    st.error(f"保存失败：{e}")

        if st.session_state.get(f"_route_trigger_{day_key}"):
            render_map_and_route(day_key, stops_by_day.get(day_key, []), st.session_state["map_state"]["mode_per_day"].get(day_key, "walking"), api_base)
