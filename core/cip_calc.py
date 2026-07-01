"""
CIP清洗计算模块

公式：
  清洗液总体积 = 系统持液量 + 管路容积 + 清洗箱体积
  药剂投加量 = 清洗液总体积 × 目标浓度 ÷ 原液浓度 × 药剂密度
"""
from typing import Dict, Any


def calculate_cip(
    system_hold_up: float,          # 系统持液量 L
    pipe_volume: float,             # 管路容积 L
    tank_volume: float,             # 清洗箱体积 L
    target_concentration: float,    # 目标浓度 %
    stock_concentration: float,     # 药剂原液浓度 %
    chemical_density: float,        # 药剂密度 kg/L
    chemical_name: str = "",        # 药剂名称
    recommended_time: int = 60,     # 建议清洗时间 min
    cleaning_flow_rate: float = 0,  # 清洗循环流量 m³/h
) -> Dict[str, Any]:
    """CIP清洗计算"""
    # 参数校验
    if system_hold_up < 0:
        raise ValueError("系统持液量不能为负数")
    if pipe_volume < 0:
        raise ValueError("管路容积不能为负数")
    if tank_volume <= 0:
        raise ValueError("清洗箱体积必须大于0")
    if target_concentration <= 0 or target_concentration > 100:
        raise ValueError("目标浓度应在0-100%之间")
    if stock_concentration <= 0 or stock_concentration > 100:
        raise ValueError("原液浓度应在0-100%之间")
    if chemical_density <= 0:
        raise ValueError("药剂密度必须大于0")

    # 清洗液总体积 (L)
    total_cleaning_volume = system_hold_up + pipe_volume + tank_volume

    # 药剂投加量计算
    # 纯药剂量 kg = 总体积(L) × 目标浓度(%) / 100
    pure_chemical_kg = total_cleaning_volume * target_concentration / 100

    # 实际药剂投加量: 若原液为100%（固体），直接用纯药剂量
    if stock_concentration >= 99.9:
        dose_kg = pure_chemical_kg
        dose_l = dose_kg / chemical_density if chemical_density > 0 else dose_kg
    else:
        # 液体原液投加量 L = 纯药剂量 / (原液浓度% × 密度)
        dose_l = pure_chemical_kg / (stock_concentration / 100 * chemical_density)
        dose_kg = dose_l * chemical_density

    # 清洗后冲洗水量（一般为清洗液体积的1.5-2倍）
    flush_water = total_cleaning_volume * 2.0

    # 清洗循环流量建议（清洗流速约2-3 m/s对应的量，此处做简化）
    if cleaning_flow_rate <= 0:
        cleaning_flow_rate = total_cleaning_volume / 1000 * 10  # 粗略估算，~10倍体积/时

    return {
        "chemical_name": chemical_name,
        "system_hold_up": system_hold_up,
        "pipe_volume": pipe_volume,
        "tank_volume": tank_volume,
        "total_cleaning_volume": round(total_cleaning_volume, 1),
        "target_concentration": target_concentration,
        "stock_concentration": stock_concentration,
        "pure_chemical_kg": round(pure_chemical_kg, 2),
        "dose_kg": round(dose_kg, 2),
        "dose_l": round(dose_l, 2),
        "recommended_time_min": recommended_time,
        "cleaning_flow_rate": round(cleaning_flow_rate, 2),
        "flush_water_l": round(flush_water, 1),
        "flush_water_m3": round(flush_water / 1000, 2),
    }
