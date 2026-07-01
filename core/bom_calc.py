"""
BOM清单与报价模块

根据计算结果自动生成初步BOM，支持手动修改。
"""
from typing import Dict, Any, List, Optional
import copy

# 默认BOM模板
DEFAULT_BOM_ITEMS: List[Dict[str, Any]] = [
    {"seq": 1, "name": "膜管", "spec": "待选型", "quantity": 0, "unit": "根", "price": 0, "amount": 0, "remark": "根据膜面积计算确定"},
    {"seq": 2, "name": "膜组件", "spec": "待选型", "quantity": 0, "unit": "支", "price": 0, "amount": 0, "remark": "含膜壳和端头"},
    {"seq": 3, "name": "膜架", "spec": "SS304", "quantity": 0, "unit": "套", "price": 0, "amount": 0, "remark": "根据组件数量设计"},
    {"seq": 4, "name": "进水泵", "spec": "待选型", "quantity": 1, "unit": "台", "price": 0, "amount": 0, "remark": "含变频器"},
    {"seq": 5, "name": "循环泵", "spec": "待选型", "quantity": 1, "unit": "台", "price": 0, "amount": 0, "remark": "含变频器"},
    {"seq": 6, "name": "清洗泵", "spec": "待选型", "quantity": 1, "unit": "台", "price": 0, "amount": 0, "remark": "耐酸碱"},
    {"seq": 7, "name": "压力表", "spec": "0-1.0 MPa", "quantity": 4, "unit": "个", "price": 0, "amount": 0, "remark": "隔膜式"},
    {"seq": 8, "name": "流量计", "spec": "电磁流量计", "quantity": 3, "unit": "台", "price": 0, "amount": 0, "remark": "进水/产水/浓水"},
    {"seq": 9, "name": "阀门", "spec": "手动蝶阀/球阀", "quantity": 10, "unit": "个", "price": 0, "amount": 0, "remark": "根据管径配套"},
    {"seq": 10, "name": "管道", "spec": "SS304/UPVC", "quantity": 1, "unit": "批", "price": 0, "amount": 0, "remark": "含弯头法兰"},
    {"seq": 11, "name": "清洗箱", "spec": "PE/FRP", "quantity": 1, "unit": "台", "price": 0, "amount": 0, "remark": "带搅拌"},
    {"seq": 12, "name": "电控柜", "spec": "PLC控制", "quantity": 1, "unit": "套", "price": 0, "amount": 0, "remark": "含触摸屏"},
    {"seq": 13, "name": "备品备件", "spec": "密封圈/接头", "quantity": 1, "unit": "套", "price": 0, "amount": 0, "remark": "按5%替换量"},
]


def create_bom_from_results(
    module_count: int = 0,
    tubes_per_module: int = 0,
    feed_pump_flow: float = 0,
    crossflow_pump_flow: float = 0,
    cleaning_pump_flow: float = 0,
    membrane_model: str = "",
    feed_dn: str = "",
    crossflow_dn: str = "",
    permeate_dn: str = "",
    concentrate_dn: str = "",
    cleaning_dn: str = "",
) -> List[Dict[str, Any]]:
    """根据计算结果填充BOM"""
    items = copy.deepcopy(DEFAULT_BOM_ITEMS)

    total_tubes = module_count * tubes_per_module

    for item in items:
        if item["name"] == "膜管":
            item["quantity"] = total_tubes
            item["spec"] = membrane_model or "待选型"
            item["remark"] = f"{module_count}支组件 × {tubes_per_module}根/支"
        elif item["name"] == "膜组件":
            item["quantity"] = module_count
            item["spec"] = membrane_model or "待选型"
        elif item["name"] == "膜架":
            item["quantity"] = max(1, module_count // 4)  # 每4支组件一个膜架
        elif item["name"] == "进水泵":
            item["spec"] = f"Q={feed_pump_flow:.1f} m³/h" if feed_pump_flow else "待选型"
        elif item["name"] == "循环泵":
            item["spec"] = f"Q={crossflow_pump_flow:.1f} m³/h" if crossflow_pump_flow else "待选型"
        elif item["name"] == "清洗泵":
            item["spec"] = f"Q={cleaning_pump_flow:.1f} m³/h" if cleaning_pump_flow else "待选型"
        elif item["name"] == "管道":
            item["spec"] = f"进水{feed_dn} 循环{crossflow_dn} 产水{permeate_dn} 浓水{concentrate_dn} 清洗{cleaning_dn}"

    # 计算金额
    for item in items:
        item["amount"] = round(item["quantity"] * item["price"], 2)

    return items


def calculate_bom_total(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算BOM总价"""
    total = sum(item.get("amount", 0) for item in items)
    return {
        "items": items,
        "total_amount": round(total, 2),
        "item_count": len(items),
    }
