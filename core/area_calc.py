"""
膜面积计算模块

公式：
  所需膜面积 A = 设计产水量Q × 1000 ÷ 每日运行时间H ÷ 设计通量J × 安全系数K
  Q: m³/d  H: h  J: LMH  A: m²
"""

import math
from typing import Dict, Any


def calc_module_area_from_tubes(
    tube_inner_diameter_mm: float,
    tube_length_mm: float,
    tubes_per_module: int,
) -> dict:
    """根据膜管参数计算单组件膜面积

    公式:
      单根膜面积 = π × (内径_m) × (长度_m)
      组件膜面积 = 单根膜面积 × 膜管数量
    """
    d_m = tube_inner_diameter_mm / 1000
    l_m = tube_length_mm / 1000
    single_area = round(math.pi * d_m * l_m, 4)
    module_area = round(single_area * tubes_per_module, 1)
    return {
        "tube_inner_diameter_mm": tube_inner_diameter_mm,
        "tube_length_mm": tube_length_mm,
        "tubes_per_module": tubes_per_module,
        "single_tube_area": single_area,
        "module_area": module_area,
        "formula": f"{single_area:.4f} = \u03c0 \u00d7 {d_m} \u00d7 {l_m}",
        "formula_full": f"{module_area:.1f} = {single_area:.4f} \u00d7 {tubes_per_module}",
    }


def calculate_membrane_area(
    design_flow: float,
    operating_hours: float,
    design_flux: float,
    safety_factor: float,
    module_area: float,
) -> Dict[str, Any]:
    if design_flow <= 0:
        raise ValueError("\u8bbe\u8ba1\u4ea7\u6c34\u91cf\u5fc5\u987b\u5927\u4e8e0")
    if operating_hours <= 0 or operating_hours > 24:
        raise ValueError("\u6bcf\u65e5\u8fd0\u884c\u65f6\u95f4\u5fc5\u987b\u57281-24\u5c0f\u65f6\u4e4b\u95f4")
    if design_flux <= 0:
        raise ValueError("\u8bbe\u8ba1\u901a\u91cf\u5fc5\u987b\u5927\u4e8e0")
    if safety_factor <= 0:
        raise ValueError("\u5b89\u5168\u7cfb\u6570\u5fc5\u987b\u5927\u4e8e0")
    if module_area <= 0:
        raise ValueError("\u5355\u7ec4\u4ef6\u819c\u9762\u79ef\u5fc5\u987b\u5927\u4e8e0")

    theoretical_area = design_flow / operating_hours * 1000 / design_flux
    safe_area = theoretical_area * safety_factor
    module_count_raw = safe_area / module_area
    module_count = math.ceil(module_count_raw)
    actual_area = module_count * module_area
    actual_flux = design_flow / operating_hours * 1000 / actual_area
    flux_margin = (actual_flux / design_flux - 1) * 100

    return {
        "theoretical_area": round(theoretical_area, 2),
        "safe_area": round(safe_area, 2),
        "module_count": module_count,
        "module_count_raw": round(module_count_raw, 2),
        "actual_area": round(actual_area, 2),
        "actual_flux": round(actual_flux, 2),
        "flux_margin": round(flux_margin, 1),
        "design_flux": design_flux,
        "safety_factor": safety_factor,
    }
