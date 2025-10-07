import streamlit as st
from main import TripCrew
import json
import base64
import datetime as dt
import os
from dotenv import load_dotenv

# 可选的 Lottie 动画支持
try:
    from streamlit_lottie import st_lottie  
except Exception:
    st_lottie = None

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
    # 优先 AMAP_KEY，其次 AMLP_APIKEY（你当前环境已设置此名）
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
  margin-top: 0;           /* 交由父容器对齐，不再强制上边距 */
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
    # 轻量 Lottie 动画（可选）
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
        crew = TripCrew(origin, cities, date_range, interests)
        with st.spinner("旅游行程正在规划中，请稍候..."):
            try:
                result = crew.run()
                st.success("行程已生成！")
                st.markdown("### 结果", help="你可以在下方导出 Markdown 文档")
                result_str = str(result)
                st.markdown(f"<div class='result-card'>{result_str}</div>", unsafe_allow_html=True)

                # 导出下载按钮（Markdown 文件）
                data = result_str.encode("utf-8")
                b64 = base64.b64encode(data).decode()
                href = f'<a href="data:file/text;base64,{b64}" download="trip_plan.md">📥 下载 Markdown</a>'
                st.markdown(href, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"运行失败：{type(e).__name__}: {e}")



