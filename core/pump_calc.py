"""
泵选型计算模块

包含：进水泵、循环泵、清洗泵选型
公式：
  轴功率 P = Q × H × ρ × g ÷ η ÷ 3600000
  Q: m³/h  H: m  ρ: kg/m³  g: 9.81 m/s²  η: 0.55-0.65
"""
from typing import Dict, Any

GRAVITY = 9.81
WATER_DENSITY = 1000.0  # kg/m³

# 膜类型对应的推荐进水泵扬程范围
MEMBRANE_FEED_HEAD_MAP = {
    "UF": {"range": (20, 30), "default": 25, "note": "超滤膜，低压运行"},
    "NF": {"range": (50, 200), "default": 100, "note": "纳滤膜，中压运行"},
    "RO": {"range": (100, 400), "default": 150, "note": "反渗透膜，高压运行"},
    "MF": {"range": (10, 20), "default": 15, "note": "微滤膜，低压运行"},
    "TR/NF": {"range": (30, 100), "default": 60, "note": "管式纳滤膜，中压运行"},
}

# 膜类型对应的推荐回收率
MEMBRANE_RECOVERY_MAP = {
    "UF": {"range": (85, 95), "default": 90},
    "NF": {"range": (70, 85), "default": 75},
    "RO": {"range": (65, 80), "default": 75},
    "MF": {"range": (90, 98), "default": 95},
    "TR/NF": {"range": (70, 85), "default": 75},
}

def suggest_feed_pump_params(membrane_type="UF", feed_flow=500):
    mt = membrane_type.upper().split()[0]
    head_info = MEMBRANE_FEED_HEAD_MAP.get(mt, MEMBRANE_FEED_HEAD_MAP["UF"])
    rec_info = MEMBRANE_RECOVERY_MAP.get(mt, MEMBRANE_RECOVERY_MAP["UF"])
    actual_feed = round(feed_flow / (rec_info["default"] / 100), 1)
    return {
        "membrane_type": mt,
        "head_range": head_info["range"],
        "default_head": head_info["default"],
        "head_note": head_info["note"],
        "default_recovery": rec_info["default"],
        "recovery_range": rec_info["range"],
        "actual_feed_flow": actual_feed,
        "flow_note": f"进水量 = 产水量({feed_flow}) / 回收率({rec_info['default']}%) = {actual_feed} m³/h",
    }



def calculate_pump_power(
    flow_m3h: float,       # 流量 m³/h
    head_m: float,         # 扬程 m
    efficiency: float = 0.60,  # 泵效率
    density: float = WATER_DENSITY,  # 介质密度
) -> Dict[str, Any]:
    """泵功率计算"""
    # 参数校验
    if flow_m3h <= 0:
        raise ValueError("流量必须大于0")
    if head_m <= 0:
        raise ValueError("扬程必须大于0")
    if not 0.3 <= efficiency <= 0.95:
        raise ValueError("泵效率应在0.3-0.95之间")

    # 轴功率 kW
    power_kw = flow_m3h * head_m * density * GRAVITY / efficiency / 3600000

    # 电机功率（取1.2倍安全系数）
    motor_power_kw = power_kw * 1.2

    return {
        "flow": round(flow_m3h, 2),
        "head": round(head_m, 1),
        "efficiency": efficiency,
        "shaft_power_kw": round(power_kw, 2),
        "motor_power_kw": round(motor_power_kw, 2),
        "recommended_motor_kw": _round_motor_power(motor_power_kw),
    }


def _round_motor_power(power_kw: float) -> float:
    """取标准电机功率档"""
    standard = [0.55, 0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160]
    for s in standard:
        if s >= power_kw:
            return s
    return round(power_kw, 1)


def pump_selection(
    feed_flow: float,         # 进水流量 m³/h（已考虑回收率）
    crossflow_flow: float,    # 循环流量 m³/h
    cleaning_flow: float,     # 清洗流量 m³/h
    feed_head: float = 30,    # 进水扬程 m
    crossflow_head: float = 25,  # 循环扬程 m
    cleaning_head: float = 20,   # 清洗扬程 m
    efficiency: float = 0.60,
) -> Dict[str, Any]:
    """三泵统一选型"""
    return {
        "feed_pump": {
            "name": "进水泵",
            "flow": feed_flow,
            "head": feed_head,
            "material": "SS304/SS316L",
            **calculate_pump_power(feed_flow, feed_head, efficiency),
        },
        "crossflow_pump": {
            "name": "循环泵",
            "flow": crossflow_flow,
            "head": crossflow_head,
            "material": "SS304/SS316L",
            **calculate_pump_power(crossflow_flow, crossflow_head, efficiency),
        },
        "cleaning_pump": {
            "name": "清洗泵",
            "flow": cleaning_flow,
            "head": cleaning_head,
            "material": "SS304/SS316L（耐酸碱）",
            **calculate_pump_power(cleaning_flow, cleaning_head, 0.55),
        },
    }
