"""
管径流速校核模块

公式：
  截面积 A = π × D² ÷ 4
  流速 v = Q ÷ A ÷ 3600

推荐流速：
  进水管 1.0～1.5 m/s
  循环主管 1.5～2.5 m/s
  产水管 0.5～1.0 m/s
  浓水管 1.0～2.0 m/s
  清洗管 1.0～2.0 m/s
"""
import math
import json
import os
from typing import Dict, Any, Tuple

# 加载DN标准
_data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_chem_path = os.path.join(_data_dir, "data", "chemical_data.json")
with open(_chem_path, "r", encoding="utf-8") as f:
    _DN_STANDARD = json.load(f)["pipe_dn_standard"]

# 各管路推荐流速范围 (m/s)
FLOW_VELOCITY_RANGE = {
    "进水": (1.0, 1.5),
    "循环主管": (1.5, 2.5),
    "产水": (0.5, 1.0),
    "浓水": (1.0, 2.0),
    "清洗": (1.0, 2.0),
}


def _calc_velocity(flow_m3h: float, inner_dia_m: float) -> float:
    """计算流速 m/s"""
    area = math.pi * inner_dia_m ** 2 / 4
    if area <= 0:
        return float("inf")
    return flow_m3h / area / 3600


def recommend_dn(
    flow_m3h: float,
    pipe_type: str = "进水",
) -> Dict[str, Any]:
    """推荐管径并校核流速"""
    # 参数校验
    if flow_m3h <= 0:
        raise ValueError("流量必须大于0")
    if pipe_type not in FLOW_VELOCITY_RANGE:
        raise ValueError(f"不支持的管路类型: {pipe_type}")

    v_min, v_max = FLOW_VELOCITY_RANGE[pipe_type]

    # 遍历DN标准，找流速在推荐范围内的最小管径
    candidates = []
    for dn in _DN_STANDARD:
        v = _calc_velocity(flow_m3h, dn["inner_diameter"])
        dn["velocity"] = v
        in_range = v_min <= v <= v_max
        dn["in_range"] = in_range
        candidates.append(dn)

    # 选择流速在推荐范围内的最小DN
    recommended = None
    for c in candidates:
        if c["in_range"]:
            recommended = c
            break

    # 如果没有完全符合的，选流速最接近范围的
    if recommended is None:
        best = min(candidates, key=lambda x: abs(x["velocity"] - (v_min + v_max) / 2))
        recommended = best

    actual_velocity = recommended["velocity"]

    # 判断
    if actual_velocity < v_min:
        advice = f"流速偏低({actual_velocity:.2f} m/s)，管径偏大，可能增加投资成本。可考虑{dn_smaller(recommended['dn'])}"
        risk = "投资偏高"
    elif actual_velocity > v_max:
        advice = f"流速偏高({actual_velocity:.2f} m/s)，可能增加沿程水头损失和冲刷磨损。建议选用{next_larger_dn(recommended['dn'])}"
        risk = "水头损失大，可能磨损管道"
    else:
        advice = f"流速({actual_velocity:.2f} m/s)在推荐范围内，选型合理"
        risk = "无"

    return {
        "flow": flow_m3h,
        "pipe_type": pipe_type,
        "recommended_dn": recommended["dn"],
        "inner_diameter_mm": round(recommended["inner_diameter"] * 1000, 1),
        "actual_velocity": round(actual_velocity, 2),
        "velocity_range": f"{v_min}～{v_max} m/s",
        "advice": advice,
        "risk": risk,
        "candidates": [
            {"dn": c["dn"], "velocity": round(c["velocity"], 2), "in_range": c["in_range"]}
            for c in candidates
        ],
    }


def dn_smaller(current_dn: str) -> str:
    """返回比当前DN小一级的管径"""
    for i, dn in enumerate(_DN_STANDARD):
        if dn["dn"] == current_dn and i > 0:
            s = _DN_STANDARD[i - 1]["dn"]
            return f"降为{s}"
    return "已是最小DN"


def next_larger_dn(current_dn: str) -> str:
    """返回比当前DN大一级的管径"""
    for i, dn in enumerate(_DN_STANDARD):
        if dn["dn"] == current_dn and i < len(_DN_STANDARD) - 1:
            n = _DN_STANDARD[i + 1]["dn"]
            return f"增大到{n}"
    return "已是最大DN"
