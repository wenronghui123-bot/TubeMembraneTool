"""
泡点检测模块 — 用于管式膜生产过程单根膜管检测

默认建议：
  初始压力：0.05 MPa
  升压步长：0.02～0.05 MPa
  单档稳压：30～60秒
  常规检测：0.15 MPa 保压5分钟
  严格检测：0.20 MPa 保压5分钟
"""
from typing import Dict, Any, List
from datetime import date


def record_bubble_point_test(
    tube_id: str,                 # 膜管编号
    model: str,                   # 膜型号
    pore_size: str,               # 膜孔径
    wetting_liquid: str,          # 润湿液
    wetting_time_min: float,      # 润湿时间 min
    test_pressure_mpa: float,     # 检测压力 MPa
    hold_time_min: float,         # 保压时间 min
    continuous_bubbling: bool,    # 是否连续冒泡
    bubble_position: str,         # 冒泡位置
    pressure_drop: float,         # 压降值 MPa
    tester: str,                  # 检测人员
    test_date: str = "",          # 检测日期
) -> Dict[str, Any]:
    """记录单根膜管泡点检测"""
    # 参数校验
    if not tube_id.strip():
        raise ValueError("膜管编号不能为空")
    if test_pressure_mpa <= 0:
        raise ValueError("检测压力必须大于0")
    if hold_time_min <= 0:
        raise ValueError("保压时间必须大于0")
    if pressure_drop < 0:
        raise ValueError("压降值不能为负数")

    if not test_date:
        test_date = date.today().isoformat()

    # 判定标准：固定位置连续冒泡 → 不合格
    is_qualified = not continuous_bubbling

    # 压降判定（辅助）：压降超过0.01 MPa也可能异常
    if pressure_drop > 0.01:
        drop_warning = f"压降较大({pressure_drop:.3f} MPa)，建议关注"
    else:
        drop_warning = "压降在正常范围内"

    return {
        "tube_id": tube_id,
        "model": model,
        "pore_size": pore_size,
        "wetting_liquid": wetting_liquid,
        "wetting_time_min": wetting_time_min,
        "test_pressure_mpa": test_pressure_mpa,
        "hold_time_min": hold_time_min,
        "continuous_bubbling": continuous_bubbling,
        "bubble_position": bubble_position,
        "pressure_drop": pressure_drop,
        "tester": tester,
        "test_date": test_date,
        "is_qualified": is_qualified,
        "result": "合格" if is_qualified else "不合格",
        "drop_warning": drop_warning,
    }


def batch_test_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """批量检测统计"""
    total = len(records)
    if total == 0:
        return {"total": 0, "qualified": 0, "failed": 0, "pass_rate": 0.0}

    qualified = sum(1 for r in records if r["is_qualified"])
    failed = total - qualified
    pass_rate = qualified / total * 100

    return {
        "total": total,
        "qualified": qualified,
        "failed": failed,
        "pass_rate": round(pass_rate, 1),
        "records": records,
    }
