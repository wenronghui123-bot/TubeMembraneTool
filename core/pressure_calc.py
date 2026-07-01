"""
跨膜压差(TMP)与压力校核模块

公式：
  跨膜压差 TMP = (进膜压力 + 出膜压力) ÷ 2 - 产水侧压力
"""
from typing import Dict, Any


def calculate_tmp(
    inlet_pressure: float,      # 进膜压力 MPa
    outlet_pressure: float,     # 出膜压力 MPa
    permeate_pressure: float,   # 产水侧压力 MPa
    max_pressure: float = 0.6,  # 最大允许运行压力 MPa
) -> Dict[str, Any]:
    """计算跨膜压差(TMP)及压力校核"""
    # 参数校验
    if inlet_pressure < 0:
        raise ValueError("进膜压力不能为负数")
    if outlet_pressure < 0:
        raise ValueError("出膜压力不能为负数")
    if permeate_pressure < 0:
        raise ValueError("产水侧压力不能为负数")
    if outlet_pressure > inlet_pressure:
        raise ValueError("出膜压力不能大于进膜压力")

    # TMP (MPa)
    tmp_mpa = (inlet_pressure + outlet_pressure) / 2 - permeate_pressure
    # 跨膜压差 (kPa)
    tmp_kpa = tmp_mpa * 1000

    # 进出口压差 (MPa)
    dp = inlet_pressure - outlet_pressure
    dp_kpa = dp * 1000

    # 压力校核
    warnings = []
    status = "正常"

    if tmp_mpa < 0:
        warnings.append("跨膜压差为负数，请检查压力表读数")
        status = "异常"

    if tmp_mpa > max_pressure * 0.85:
        warnings.append(f"跨膜压差接近最大允许运行压力({tmp_mpa:.3f}  / {max_pressure} MPa)，注意膜污染风险")
        status = "警告"

    if dp > 0.15:
        warnings.append(f"进出口压差较大({dp:.3f} MPa)，可能存在膜堵塞或浓水通道不畅")
        status = "警告"
    if dp > 0.25:
        warnings.append("进出口压差过大，建议立即在线清洗(CIP)")
        status = "异常"

    if inlet_pressure > max_pressure:
        warnings.append(f"进膜压力({inlet_pressure:.3f} MPa)超过膜元件最大允许压力({max_pressure} MPa)")
        status = "异常"

    # 跨膜压差建议范围：UF 0.05-0.3 MPa, NF/RO 0.3-2.0 MPa（取决于膜类型）
    if not warnings:
        warnings.append("跨膜压差在正常范围内")

    return {
        "inlet_pressure": inlet_pressure,
        "outlet_pressure": outlet_pressure,
        "permeate_pressure": permeate_pressure,
        "tmp_mpa": round(tmp_mpa, 4),
        "tmp_kpa": round(tmp_kpa, 1),
        "dp_mpa": round(dp, 4),
        "dp_kpa": round(dp_kpa, 1),
        "status": status,
        "warnings": warnings,
        "max_pressure": max_pressure,
    }
