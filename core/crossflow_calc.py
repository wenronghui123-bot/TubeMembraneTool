"""
错流循环量计算模块

工业设计中膜组件按串流(series)排列：
  每串最多6支组件，通常5支一串
  系统总循环量 = 单组件循环量 × 串数
  串数 = ceil(组件总数 / 每串组件数)
  每串配一台循环泵
"""
import math
from typing import Dict, Any


def calculate_crossflow(
    tube_inner_diameter: float,
    tubes_per_module: int,
    crossflow_velocity: float,
    module_count: int,
    modules_per_string: int = 5,
) -> Dict[str, Any]:
    if tube_inner_diameter <= 0:
        raise ValueError("膜管内径必须大于0")
    if tubes_per_module <= 0:
        raise ValueError("单组件膜管数量必须大于0")
    if crossflow_velocity <= 0:
        raise ValueError("错流速度必须大于0")
    if module_count <= 0:
        raise ValueError("组件数量必须大于0")
    if modules_per_string <= 0 or modules_per_string > 6:
        raise ValueError("每串组件数必须在1-6之间")

    d_m = tube_inner_diameter / 1000
    single_tube_area = math.pi * d_m ** 2 / 4
    module_flow_area = single_tube_area * tubes_per_module
    single_module_flow = module_flow_area * crossflow_velocity * 3600

    string_count = math.ceil(module_count / modules_per_string)
    actual_per_string = module_count / string_count
    total_crossflow = single_module_flow * string_count

    if actual_per_string > 6:
        series_advice = f"每串{actual_per_string:.0f}支，超过6支上限，建议增加串数或减少每串支数"
    elif actual_per_string > 5:
        series_advice = f"每串{actual_per_string:.0f}支，接近上限(6支)，建议调整为5支/串"
    else:
        series_advice = f"每串{actual_per_string:.0f}支，串流配置合理"

    if crossflow_velocity < 1.5:
        velocity_advice = "偏低：可能导致膜污染加速，建议提高至≥2.0 m/s"
    elif crossflow_velocity < 3.0:
        velocity_advice = "合理：适用于NF/RO膜"
    elif crossflow_velocity <= 4.5:
        velocity_advice = "合理：适用于UF/MF膜"
    else:
        velocity_advice = "偏高：能耗较大，确认膜管耐冲刷性能"

    return {
        "single_tube_area": round(single_tube_area, 8),
        "module_flow_area": round(module_flow_area, 6),
        "single_module_flow": round(single_module_flow, 2),
        "modules_per_string": modules_per_string,
        "string_count": string_count,
        "actual_per_string": round(actual_per_string, 1),
        "series_advice": series_advice,
        "total_crossflow": round(total_crossflow, 2),
        "recommended_pump_flow": round(total_crossflow * 1.15, 2),
        "pump_count": string_count,
        "velocity_advice": velocity_advice,
        "crossflow_velocity": crossflow_velocity,
    }
