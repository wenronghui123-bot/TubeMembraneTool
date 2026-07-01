"""
管式膜设计计算工具 - Streamlit 浏览器版
运行: streamlit run app.py
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streamlit as st
from datetime import date
st.set_page_config(page_title="管式膜计算工具_大辉哥专用版", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")
from core.area_calc import calculate_membrane_area, calc_module_area_from_tubes
from core.crossflow_calc import calculate_crossflow
from core.pressure_calc import calculate_tmp
from core.pump_calc import pump_selection, suggest_feed_pump_params
from core.pipe_calc import recommend_dn
from core.cip_calc import calculate_cip
from core.bubble_point_calc import record_bubble_point_test, batch_test_summary
from core.bom_calc import create_bom_from_results

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
# GitHub API helpers for cloud persistence
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "wenronghui123-bot/TubeMembraneTool"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") is not None or GITHUB_TOKEN != ""

def _cloud_load(filename):
    """Load a JSON file from GitHub repo (cloud mode)"""
    import requests
    url = f"{GITHUB_API}/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            import base64
            content = base64.b64decode(r.json()["content"]).decode()
            return json.loads(content)
    except Exception:
        pass
    return None

def _cloud_save(filename, data, message="Update via app"):
    """Save a JSON file to GitHub repo (cloud mode)"""
    import requests, base64
    url = f"{GITHUB_API}/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode()
    b64 = base64.b64encode(content_bytes).decode()
    payload = {"message": message, "content": b64}
    try:
        existing = requests.get(url, headers=headers, timeout=10)
        if existing.status_code == 200:
            payload["sha"] = existing.json()["sha"]
        r = requests.put(url, headers=headers, json=payload, timeout=15)
        return r.status_code in [200, 201]
    except Exception:
        pass
    return False

def _load(fn):
    with open(os.path.join(DATA_DIR, fn), "r", encoding="utf-8") as f:
        return json.load(f)

# Load membrane models: cloud first, local fallback
_raw = _cloud_load("data/membrane_models.json") if IS_CLOUD else None
if _raw is None:
    _raw = _load("membrane_models.json")
membrane_models_raw = _raw
# Load membrane models into session state for live updates
if "membrane_models" not in st.session_state:
    st.session_state.membrane_models = membrane_models_raw[:]
membrane_models = st.session_state.membrane_models
chemical_data = _cloud_load("data/chemical_data.json") if IS_CLOUD else None
if chemical_data is None:
    chemical_data = _load("chemical_data.json")
# Pure-Python helpers (replaces pandas DataFrame operations)
def _uq(items, key):
    """Unique sorted values for a key from list of dicts"""
    return sorted(set(str(d.get(key, "")).strip() for d in items if d.get(key)))

def _filt_by_list(items, key, values):
    """Filter list of dicts where key value is in values list"""
    return [d for d in items if d.get(key) in values]

def _filt_by_kw(items, keyword):
    """Filter list of dicts where any string field contains keyword (case-insensitive)"""
    kw = keyword.lower()
    return [d for d in items if any(kw in str(v).lower() for v in d.values())]

def _filt_by_range(items, key, min_val, max_val):
    """Filter list of dicts by numeric range"""
    return [d for d in items if min_val <= (d.get(key) or 0) <= max_val]


def _load_experiments():
    if IS_CLOUD:
        data = _cloud_load("data/membrane_experiments.json")
        if data is not None:
            return data
    exp_file = os.path.join(DATA_DIR, "membrane_experiments.json")
    if os.path.exists(exp_file):
        with open(exp_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# Initialize session state
for k in ["project", "membrane", "area_result", "crossflow_result", "pressure_result", "pump_result", "pipe_result", "cip_result", "bubble_records", "bom_items"]:
    if k not in st.session_state:
        if k == "bubble_records":
            st.session_state[k] = []
        else:
            st.session_state[k] = {}

if "experiments" not in st.session_state:
    st.session_state.experiments = _load_experiments()


BOM_ITEMS_DEFAULT = create_bom_from_results()
if not st.session_state.bom_items:
    st.session_state.bom_items = BOM_ITEMS_DEFAULT

st.sidebar.title("🔬 管式膜计算工具_大辉哥专用版")
st.sidebar.caption("TubularMembraneDesignTool v1.0")
st.sidebar.divider()

nav_items = [
    "📋 项目基础信息",
    "🗄️ 膜型号数据库",
    "📐 膜面积计算",
    "🔄 错流循环量计算",
    "📊 TMP与压力校核",
    "⚙️ 泵与管径选型",
    "🧪 CIP清洗计算",
    "🫫 泡点检测记录",
    "📦 BOM清单与报价",
    "📤 报告导出",
    "🧫 膜实验记录",
]

page = st.sidebar.radio("功能导航", nav_items)

def _collect():
    c = {}
    if st.session_state.project:
        c["项目基础信息"] = st.session_state.project
    if st.session_state.membrane:
        c["膜型号"] = st.session_state.membrane
    if st.session_state.area_result:
        c["膜面积计算"] = st.session_state.area_result
    if st.session_state.crossflow_result:
        c["错流循环量"] = st.session_state.crossflow_result
    if st.session_state.pressure_result:
        c["TMP压力校核"] = st.session_state.pressure_result
    if st.session_state.pump_result:
        c["泵选型"] = st.session_state.pump_result
    if st.session_state.pipe_result:
        c["管径选型"] = st.session_state.pipe_result
    if st.session_state.cip_result:
        c["CIP清洗"] = st.session_state.cip_result
    if st.session_state.bubble_records:
        c["泡点检测"] = batch_test_summary(st.session_state.bubble_records)
    items = st.session_state.bom_items
    total = sum(it.get("quantity", 0) * it.get("price", 0) for it in items)
    c["BOM清单"] = {"items": items, "total": total}
    return c

# ==== Project Info Page ====
if page == nav_items[0]:
    st.header("项目基础信息")
    c1, c2, c3 = st.columns(3)
    with c1:
        pn = st.text_input("项目名称", value=st.session_state.project.get("project_name", ""))
        pno = st.text_input("项目编号", value=st.session_state.project.get("project_no", ""))
        cust = st.text_input("客户名称", value=st.session_state.project.get("customer", ""))
    with c2:
        df_val = st.number_input("设计产水量 (m³/d)", 1.0, 100000.0, float(st.session_state.project.get("design_flow", 500)), 10.0)
        wt = st.selectbox("水型", ["工业废水", "市政污水", "垃圾渗滤液", "电镀废水", "印染废水", "养殖废水", "其他"])
    with c3:
        des = st.text_input("设计人员", value=st.session_state.project.get("designer", ""))
        dd = st.date_input("设计日期", date.today())
        rem = st.text_area("备注", value=st.session_state.project.get("remark", ""), height=80)
    if st.button("保存并应用到计算", type="primary", use_container_width=True):
        st.session_state.project = {"project_name": pn, "project_no": pno, "customer": cust, "design_flow": df_val, "water_type": wt, "designer": des, "design_date": str(dd), "remark": rem}
        st.success(f"项目 [{pn}] 已保存")

# ==== Membrane Database Page ====
elif page == nav_items[1]:
    st.header("膜型号数据库")

    # ---- Filters ----
    # Use membrane_models directly (list of dicts)
    # Note: filter values extracted from membrane_models list

    # Extract unique filter values
    all_mfrs = _uq(membrane_models, "manufacturer")
    all_types = _uq(membrane_models, "type")
    all_countries = _uq(membrane_models, "country")
    all_categories = _uq(membrane_models, "category") if membrane_models and "category" in membrane_models[0] else []

    with st.expander("筛选条件 (Filter)", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_mfrs = st.multiselect("制造商 (品牌)", all_mfrs, default=[])
            sel_types = st.multiselect("膜类型", all_types, default=[])
        with c2:
            sel_countries = st.multiselect("国家", all_countries, default=[])
            if all_categories:
                sel_categories = st.multiselect("膜结构", all_categories, default=[])
            else:
                sel_categories = []
        with c3:
            keyword = st.text_input("关键字搜索", placeholder="输入型号/材质/描述...")
            area_range = st.slider("膜面积范围 (m2)", 0.0, 200.0, (0.0, 200.0), 1.0)

    # Apply filters
    df_filtered = list(membrane_models)
    if sel_mfrs:
        df_filtered = _filt_by_list(df_filtered, "manufacturer", sel_mfrs)
    if sel_types:
        df_filtered = _filt_by_list(df_filtered, "type", sel_types)
    if sel_countries:
        df_filtered = _filt_by_list(df_filtered, "country", sel_countries)
    if sel_categories:
        df_filtered = _filt_by_list(df_filtered, "category", sel_categories)
    if keyword:
        df_filtered = _filt_by_kw(df_filtered, keyword)
    if df_filtered and "module_area" in df_filtered[0]:
        df_filtered = _filt_by_range(df_filtered, "module_area", area_range[0], area_range[1])

    # Display - Editable Table
    st.caption(f"筛选结果: {len(df_filtered)} / {len(membrane_models)} 个膜型号 (点击单元格直接编辑)")

    col_map = {"model": "膜型号", "manufacturer": "制造商", "country": "国家", "type": "膜类型", "material": "膜材质", "pore_size": "孔径", "tube_inner_diameter": "膜管内径（mm）", "tube_length": "膜管长度（mm）", "single_tube_area": "单根膜面积（m2）", "tubes_per_module": "单组件膜管数", "module_area": "膜面积（m2）", "recommended_flux": "推荐通量（LMH）", "recommended_crossflow_velocity": "推荐错流速度（m/s）", "clean_water_flux": "清水通量（LMH）", "max_pressure": "最大运行压力（MPa）", "ph_range": "运行pH范围", "cleaning_ph_range": "清洗pH范围", "max_temperature": "最高运行温度（℃）", "connection_spec": "接口规格", "housing_material": "壳体材质", "description": "描述/备注", "category": "膜结构类别"}
    display_keys = [k for k in ["model","manufacturer","country","type","material","pore_size","module_area","recommended_flux","clean_water_flux","max_pressure","ph_range","cleaning_ph_range","max_temperature","connection_spec","housing_material","description","category"] if df_filtered and k in df_filtered[0]]
    display_data = [{col_map.get(k, k): d.get(k) for k in display_keys} for d in df_filtered]
    edited_df = st.data_editor(display_data, use_container_width=True, hide_index=True, num_rows="dynamic", key="membrane_editor")


    c_save, c_select = st.columns([1, 3])
    with c_save:
        if st.button("保存修改", type="primary"):
            # Convert Chinese column names back to original keys
            reverse_map = {v: k for k, v in col_map.items()}
            edited_dicts = [{reverse_map.get(k, k): v for k, v in d.items()} for d in edited_df]
            # Merge edits: update existing models by model name, keep filtered-out models unchanged
            full_models = list(membrane_models)
            edited_models = {d["model"]: d for d in edited_dicts if d.get("model")}
            for i, m in enumerate(full_models):
                if m.get("model") in edited_models:
                    full_models[i] = edited_models[m["model"]]
                    del edited_models[m["model"]]
            # Add any new models
            full_models.extend(edited_models.values())
            db_path = os.path.join(os.path.dirname(__file__), "data", "membrane_models.json")
            if IS_CLOUD:
                _cloud_save("data/membrane_models.json", full_models)
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(full_models, f, ensure_ascii=False, indent=2)
            st.session_state.membrane_models = full_models
            membrane_models.clear()
            membrane_models.extend(full_models)
            st.success(f"已保存 {len(full_models)} 个膜型号 (修改{len(edited_dicts)}个)")
            st.rerun()

    st.divider()
    st.subheader("选用膜型号到计算")
    model_names = [m["model"] for m in membrane_models if m.get("model")]
    sel_model = st.selectbox("选择膜型号", model_names, key="membrane_select")
    if st.button("选用此型号", type="primary"):
        for m in membrane_models:
            if m["model"] == sel_model:
                st.session_state.membrane = m
                st.success(f"已选用: {m['manufacturer']} {m['model']}")
                break


# ==== Area Calculation Page ====
elif page == nav_items[2]:
    st.header("膜面积计算")
    c1, c2 = st.columns(2)
    with c1:
        qa = st.number_input("设计产水量 (m\u00b3/d)", 1.0, 100000.0, float(st.session_state.project.get("design_flow", 500)), 1.0)
        ha = st.number_input("每日运行时间 (h)", 1, 24, 20)
        ja = st.number_input("设计通量 (LMH)", 1.0, 500.0, float(st.session_state.membrane.get("recommended_flux", 60)), 1.0)
    with c2:
        ka = st.number_input("安全系数", 1.0, 2.0, 1.15, 0.01)
        ma_val = st.number_input("单组件膜面积 (m\u00b2)", 1.0, 500.0, float(st.session_state.membrane.get("module_area", 12.6)), 0.1)
    if st.button("开始计算", type="primary", use_container_width=True):
        try:
            r = calculate_membrane_area(qa, ha, ja, ka, ma_val)
            st.session_state.area_result = r
        except ValueError as e:
            st.error(f"输入错误: {e}")
    if st.session_state.area_result:
        r = st.session_state.area_result
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("理论膜面积", f"{r['theoretical_area']:.2f} m\u00b2")
        c2.metric("安全放大后", f"{r['safe_area']:.2f} m\u00b2")
        c3.metric("推荐组件数", f"{r['module_count']} 支")
        c4.metric("实际通量", f"{r['actual_flux']:.2f} LMH")
        st.metric("实际配置膜面积", f"{r['actual_area']:.2f} m\u00b2")
        st.caption(f"通量余量: {r['flux_margin']:.1f}%")
# ==== Crossflow Calculation Page ====
elif page == nav_items[3]:
    st.header("错流循环量计算")
    c1, c2 = st.columns(2)
    with c1:
        td = st.number_input("膜管内径 (mm)", 1.0, 100.0, float(st.session_state.membrane.get("tube_inner_diameter", 8.0)), 0.1)
        tn = st.number_input("单组件膜管数量", 1, 10000, int(st.session_state.membrane.get("tubes_per_module", 365)))
    with c2:
        tv = st.number_input("错流速度 (m/s)", 0.5, 10.0, float(st.session_state.membrane.get("recommended_crossflow_velocity", 3.5)), 0.1)
        mc_val = st.number_input("组件数量", 1, 500, st.session_state.area_result.get("module_count", 20))
    if st.button("计算错流循环量", type="primary", use_container_width=True):
        try:
            r = calculate_crossflow(td, tn, tv, mc_val)
            st.session_state.crossflow_result = r
        except ValueError as e:
            st.error(f"输入错误: {e}")
    if st.session_state.crossflow_result:
        r = st.session_state.crossflow_result
        c1, c2, c3 = st.columns(3)
        c1.metric("单组件循环量", f"{r['single_module_flow']:.2f} m\u00b3/h")
        c2.metric("系统总循环量", f"{r['total_crossflow']:.2f} m\u00b3/h")
        c3.metric("推荐循环泵流量", f"{r['recommended_pump_flow']:.2f} m\u00b3/h")
        st.info(r['velocity_advice'])
# ==== TMP Pressure Page ====
elif page == nav_items[4]:
    st.header("TMP与压力校核")
    c1, c2 = st.columns(2)
    with c1:
        pi = st.number_input("进膜压力 (MPa)", 0.0, 10.0, 0.35, 0.01)
        po = st.number_input("出膜压力 (MPa)", 0.0, 10.0, 0.25, 0.01)
    with c2:
        pp = st.number_input("产水侧压力 (MPa)", 0.0, 10.0, 0.05, 0.01)
        pm = st.number_input("最大允许压力 (MPa)", 0.1, 10.0, float(st.session_state.membrane.get("max_pressure", 0.6)), 0.01)
    if st.button("TMP计算与校核", type="primary", use_container_width=True):
        try:
            r = calculate_tmp(pi, po, pp, pm)
            st.session_state.pressure_result = r
        except ValueError as e:
            st.error(f"输入错误: {e}")
    if st.session_state.pressure_result:
        r = st.session_state.pressure_result
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TMP (MPa)", f"{r['tmp_mpa']:.4f}")
        c2.metric("TMP (kPa)", f"{r['tmp_kpa']:.1f}")
        c3.metric("压差 (MPa)", f"{r['dp_mpa']:.4f}")
        c4.metric("压差 (kPa)", f"{r['dp_kpa']:.1f}")
        sc_map = {"正常": "green", "警告": "orange", "异常": "red"}
        st.markdown(f"校核状态: :{sc_map.get(r['status'], 'gray')}[{r['status']}]")
        for w in r['warnings']:
            st.warning(w) if "正常" not in w else st.success(w)
# ==== Pump and Pipe Page ====
elif page == nav_items[5]:
    st.header("泵与管径选型")
    t1, t2 = st.tabs(["泵选型", "管径选型"])
    with t1:
        c1, c2, c3 = st.columns(3)
        with c1:
            qf_p = st.number_input("进水流量 (m\u00b3/h)", 0.0, 5000.0, 25.0, 1.0, key="qf")
            qc_p = st.number_input("循环流量 (m\u00b3/h)", 0.0, 50000.0, st.session_state.crossflow_result.get("recommended_pump_flow", 200.0), 1.0, key="qc")
        with c2:
            qcl_p = st.number_input("清洗流量 (m\u00b3/h)", 0.0, 5000.0, 50.0, 1.0, key="qcl")
            hf_p = st.number_input("进水扬程 (m)", 1, 200, 30, key="hf")
        with c3:
            hc_p = st.number_input("循环扬程 (m)", 1, 200, 25, key="hc")
            hcl_p = st.number_input("清洗扬程 (m)", 1, 200, 20, key="hcl")
        eff = st.slider("泵效率", 0.30, 0.95, 0.60, 0.01)
        if st.button("泵选型计算", type="primary"):
            try:
                r = pump_selection(qf_p, qc_p, qcl_p, hf_p, hc_p, hcl_p, eff)
                st.session_state.pump_result = r
            except ValueError as e:
                st.error(f"输入错误: {e}")
        if st.session_state.pump_result:
            r = st.session_state.pump_result
            rows = []
            for k in ["feed_pump", "crossflow_pump", "cleaning_pump"]:
                p = r[k]
                rows.append({"泵名称": p["name"], "流量 m\u00b3/h": f"{p['flow']:.1f}", "扬程 m": f"{p['head']:.0f}", "轴功率 kW": f"{p['shaft_power_kw']:.2f}", "电机 kW": f"{p['recommended_motor_kw']:.0f}", "材质": p["material"]})
            st.dataframe(rows, use_container_width=True, hide_index=True)
    with t2:
        st.subheader("管径选型")
        if st.button("管径选型计算", type="primary"):
            pipes = []
            for pt, pf in zip(["进水", "循环主管", "产水", "浓水", "清洗"], [qf_p, qc_p, max(qf_p * 0.9, 0.1), max(qc_p * 0.9, 0.1), qcl_p]):
                try:
                    pipes.append(recommend_dn(max(pf, 0.1), pt))
                except ValueError as e:
                    st.error(f"{pt}: {e}")
            st.session_state.pipe_result = {"pipes": pipes}
        if st.session_state.pipe_result:
            rows = []
            for p in st.session_state.pipe_result["pipes"]:
                rows.append({"管路类型": p["pipe_type"], "流量 m\u00b3/h": f"{p['flow']:.1f}", "推荐DN": p["recommended_dn"], "内径 mm": p["inner_diameter_mm"], "流速 m/s": f"{p['actual_velocity']:.2f}", "评价": p["advice"]})
            st.dataframe(rows, use_container_width=True, hide_index=True)
# ==== CIP Page ====
elif page == nav_items[6]:
    st.header("CIP清洗计算")
    chems = [c["name"] for c in chemical_data["chemicals"]]
    cs = st.selectbox("药剂类型", chems)
    chem = chemical_data["chemicals"][chems.index(cs)]
    c1, c2 = st.columns(2)
    with c1:
        sh = st.number_input("系统持液量 (L)", 0.0, 1000000.0, 500.0, 10.0)
        pv = st.number_input("管路容积 (L)", 0.0, 1000000.0, 200.0, 10.0)
        tva = st.number_input("清洗箱体积 (L)", 1.0, 1000000.0, 1000.0, 10.0)
    with c2:
        tc = st.number_input("目标浓度 (%)", 0.01, 100.0, chem["recommended_concentration"], 0.01)
        sc = st.number_input("原液浓度 (%)", 0.1, 100.0, chem["stock_concentration"], 0.1)
        dn = st.number_input("药剂密度 (kg/L)", 0.5, 5.0, chem["density"], 0.01)
        rt = st.number_input("清洗时间 (min)", 10, 600, chem["recommended_time"])
    if st.button("CIP清洗计算", type="primary", use_container_width=True):
        try:
            r = calculate_cip(sh, pv, tva, tc, sc, dn, cs, rt)
            st.session_state.cip_result = r
        except ValueError as e:
            st.error(f"输入错误: {e}")
    if st.session_state.cip_result:
        r = st.session_state.cip_result
        c1, c2, c3 = st.columns(3)
        c1.metric("清洗液总体积", f"{r['total_cleaning_volume']:.1f} L")
        c2.metric("药剂投加量 (kg)", f"{r['dose_kg']:.2f} kg")
        c3.metric("药剂投加量 (L)", f"{r['dose_l']:.2f} L")
        st.metric("冲洗水量", f"{r['flush_water_m3']:.2f} m\u00b3")
        st.info(f"建议清洗时间: {r['recommended_time_min']} 分钟")
# ==== Bubble Point Page ====
elif page == nav_items[7]:
    st.header("泡点检测记录")
    with st.form("bf"):
        c1, c2, c3 = st.columns(3)
        with c1:
            tid = st.text_input("膜管编号", placeholder="T001")
            mod = st.text_input("膜型号", placeholder="TMBR-8-A")
            ps = st.text_input("膜孔径", value="0.03 \u03bcm")
        with c2:
            wl = st.text_input("润湿液", value="异丙醇/水")
            wt2 = st.number_input("润湿时间 (min)", 1, 600, 10)
            tp = st.number_input("检测压力 (MPa)", 0.01, 1.0, 0.15, 0.01)
        with c3:
            ht = st.number_input("保压时间 (min)", 1, 60, 5)
            cb = st.checkbox("连续冒泡")
            bp = st.text_input("冒泡位置")
            pdv = st.number_input("压降值 (MPa)", 0.0, 10.0, 0.0, 0.001)
            tester = st.text_input("检测人员")
        if st.form_submit_button("添加记录", type="primary", use_container_width=True):
            try:
                r = record_bubble_point_test(tid, mod, ps, wl, wt2, tp, ht, cb, bp, pdv, tester)
                st.session_state.bubble_records.append(r)
                st.success(f"记录已添加: {r['result']}")
            except ValueError as e:
                st.error(f"输入错误: {e}")
    if st.button("清空记录"):
        st.session_state.bubble_records.clear()
        st.rerun()
    if st.session_state.bubble_records:
        s = batch_test_summary(st.session_state.bubble_records)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总记录", s["total"])
        c2.metric("合格", s["qualified"])
        c3.metric("不合格", s["failed"])
        c4.metric("合格率", f"{s['pass_rate']:.1f}%")
        rows = []
        for r in st.session_state.bubble_records:
            rows.append({"膜管编号": r["tube_id"], "膜型号": r["model"], "压力MPa": f"{r['test_pressure_mpa']:.2f}", "保压min": r["hold_time_min"], "连续冒泡": "是" if r["continuous_bubbling"] else "否", "位置": r["bubble_position"], "压降MPa": f"{r['pressure_drop']:.3f}", "人员": r["tester"], "结果": r["result"]})
        st.dataframe(rows, use_container_width=True, hide_index=True)
# ==== BOM Page ====
elif page == nav_items[8]:
    st.header("BOM清单与报价")
    mc_val = st.session_state.area_result.get("module_count", 0)
    if st.button("根据面积计算刷新BOM"):
        st.session_state.bom_items = create_bom_from_results(module_count=mc_val)
        st.rerun()
    items = st.session_state.bom_items
    total = 0.0
    for i, item in enumerate(items):
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([0.8, 1.5, 2, 1, 0.8, 1.5, 1.5, 2])
        c1.write(str(item["seq"]))
        c2.write(item["name"])
        c3.write(str(item["spec"]))
        nq = c4.number_input("", min_value=0.0, value=float(item.get("quantity", 0)), step=1.0, key=f"nq_{i}", label_visibility="collapsed")
        c5.write(str(item.get("unit", "")))
        np = c6.number_input("", min_value=0.0, value=float(item.get("price", 0)), step=100.0, key=f"np_{i}", label_visibility="collapsed")
        amt = round(nq * np, 2)
        c7.markdown(f"¥{amt:,.0f}")
        c8.write(str(item.get("remark", "")))
        total += amt
    st.divider()
    st.markdown(f"### 总价: ¥{total:,.2f}")
# ==== Export Page ====
elif page == nav_items[9]:
    st.header("报告导出")
    st.info("导出 Excel / Word 计算书（所有模块结果自动汇总）")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("导出 Excel 计算书", type="primary", use_container_width=True):
            from reports.export_excel import export_to_excel
            out = os.path.join(os.path.dirname(__file__), "reports", "output", "计算书.xlsx")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            export_to_excel(_collect(), out)
            st.success(f"Excel已导出: {out}")
    with c2:
        if st.button("导出 Word 计算书", type="primary", use_container_width=True):
            from reports.export_word import export_to_word
            out = os.path.join(os.path.dirname(__file__), "reports", "output", "计算书.docx")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            export_to_word(_collect(), out)
            st.success(f"Word已导出: {out}")
# ==== Experiment Page ====
elif page == nav_items[10]:
    st.header("膜实验记录")
    with st.expander("新增实验记录", expanded=False):
        with st.form("add_experiment"):
            c1, c2, c3 = st.columns(3)
            with c1:
                exp_model = st.text_input("膜型号/编号 *", placeholder="如 TMBR-8-A 或 小膜A1")
                exp_date = st.date_input("实验日期")
                exp_pressure = st.number_input("操作压力 (MPa)", 0.0, 10.0, 0.1, 0.01)
            with c2:
                exp_temp = st.number_input("实验温度 (C)", 0.0, 100.0, 25.0, 0.5)
                exp_solution = st.text_input("测试溶液", placeholder="纯水 / NaCl溶液 / ...")
                exp_flux = st.number_input("清水通量 (LMH)", 0.0, 5000.0, 100.0, 1.0)
            with c3:
                exp_duration = st.number_input("测试时长 (min)", 1, 1440, 30)
                exp_permeate = st.number_input("产水量 (mL)", 0.0, 100000.0, 0.0, 1.0)
                exp_membrane_area = st.number_input("膜面积 (m2)", 0.0001, 100.0, 0.01, 0.0001, format="%.4f")
            exp_notes = st.text_area("备注", placeholder="实验现象、膜状态等...")
            if st.form_submit_button("添加实验记录", type="primary"):
                if not exp_model:
                    st.error("请输入膜型号/编号")
                else:
                    record = {"id": len(st.session_state.experiments) + 1, "model": exp_model, "date": str(exp_date), "pressure_mpa": exp_pressure, "temperature_c": exp_temp, "solution": exp_solution, "flux_lmh": exp_flux, "duration_min": exp_duration, "permeate_ml": exp_permeate, "membrane_area_m2": exp_membrane_area, "notes": exp_notes}
                    st.session_state.experiments.append(record)
                    EXP_PATH = os.path.join(os.path.dirname(__file__), "data", "membrane_experiments.json")
                    if IS_CLOUD:
                        _cloud_save("data/membrane_experiments.json", st.session_state.experiments)
                    with open(EXP_PATH, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.experiments, f, ensure_ascii=False, indent=2)
                    st.success(f"已记录实验: {exp_model} @ {exp_flux} LMH")
                    st.rerun()
    if st.session_state.experiments:
        st.subheader(f"实验记录 (共 {len(st.session_state.experiments)} 条)")
        exp_df = st.session_state.experiments  # list of dicts
        show_cols = ["id", "model", "date", "flux_lmh", "pressure_mpa", "temperature_c", "solution", "duration_min", "permeate_ml", "membrane_area_m2", "notes"]
        show_cols_exist = [c for c in show_cols if exp_df and c in exp_df[0]]
        col_names_exp = {"id": "序号", "model": "膜型号/编号", "date": "日期", "flux_lmh": "清水通量 (LMH)", "pressure_mpa": "压力 (MPa)", "temperature_c": "温度 (C)", "solution": "测试溶液", "duration_min": "时长 (min)", "permeate_ml": "产水量 (mL)", "membrane_area_m2": "膜面积 (m2)", "notes": "备注"}
        exp_display = [{col_names_exp.get(k, k): d.get(k) for k in show_cols_exist} for d in exp_df]
        st.dataframe(exp_display, use_container_width=True, hide_index=True)
        if st.button("清空所有实验记录"):
            EXP_PATH = os.path.join(os.path.dirname(__file__), "data", "membrane_experiments.json")
            if IS_CLOUD:
            _cloud_save("data/membrane_experiments.json", [])
        with open(EXP_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
            st.session_state.experiments = []
            st.rerun()
    else:
        st.info("暂无实验记录，请在上方表单中添加")
st.sidebar.divider()
st.sidebar.caption("各模块计算结果自动联动")
st.sidebar.caption("数据: data/ | 导出: reports/output/")
