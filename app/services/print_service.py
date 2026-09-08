from html import escape

from sqlalchemy.orm import Session

from app.dependencies import CurrentUser
from app.models.customer import Customer, Vehicle
from app.models.store import Store
from app.services.work_order_service import WorkOrderService

PRINT_TITLES = {
    "checkin": "接车单",
    "quote": "报价单",
    "settle": "结算单",
}


class PrintService:
    @staticmethod
    def render_html(db: Session, current_user: CurrentUser, order_id: int, doc_type: str) -> str:
        if doc_type not in PRINT_TITLES:
            doc_type = "quote"

        detail = WorkOrderService.get_detail(db, current_user, order_id)
        store = db.query(Store).filter(Store.id == current_user.store_id).first()
        customer = db.query(Customer).filter(Customer.id == detail.customer_id).first()
        vehicle = db.query(Vehicle).filter(Vehicle.id == detail.vehicle_id).first()

        store_name = escape(store.name if store else "车修宝")
        title = PRINT_TITLES[doc_type]

        item_rows = ""
        for item in detail.items:
            item_rows += f"""
            <tr>
              <td>{escape(item.name)}</td>
              <td>{item.quantity}</td>
              <td>¥{item.unit_price:.2f}</td>
              <td>¥{item.amount:.2f}</td>
            </tr>"""

        part_rows = ""
        for part in detail.parts:
            part_rows += f"""
            <tr>
              <td>{escape(part.name)}</td>
              <td>{part.quantity}</td>
              <td>¥{part.unit_price:.2f}</td>
              <td>¥{part.amount:.2f}</td>
            </tr>"""

        fuel_map = {
            "empty": "空",
            "1/4": "1/4",
            "1/2": "1/2",
            "3/4": "3/4",
            "full": "满",
        }

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>{title} - {escape(detail.order_no)}</title>
  <style>
    body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; padding: 24px; color: #333; }}
    h1 {{ text-align: center; margin-bottom: 4px; }}
    .subtitle {{ text-align: center; color: #666; margin-bottom: 24px; }}
    .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
    .total {{ text-align: right; font-size: 18px; font-weight: bold; margin-top: 12px; }}
    .footer {{ margin-top: 40px; display: flex; justify-content: space-between; color: #666; }}
    @media print {{ .no-print {{ display: none; }} body {{ padding: 0; }} }}
  </style>
</head>
<body>
  <button class="no-print" onclick="window.print()" style="margin-bottom:16px;padding:8px 16px;">打印</button>
  <h1>{store_name}</h1>
  <div class="subtitle">{title}</div>
  <div class="meta">
    <div>工单号：{escape(detail.order_no)}</div>
    <div>状态：{escape(detail.status_label)}</div>
    <div>客户：{escape(customer.name if customer else '-')}</div>
    <div>手机：{escape(customer.phone if customer else '-')}</div>
    <div>车牌：{escape(vehicle.plate_number if vehicle else '-')}</div>
    <div>车型：{escape(f"{vehicle.brand or ''} {vehicle.model or ''}".strip() if vehicle else '-')}</div>
    <div>进店里程：{detail.mileage_in or '-'} km</div>
    <div>油量：{fuel_map.get(detail.fuel_level or '', detail.fuel_level or '-')}</div>
    <div>开单时间：{detail.created_at}</div>
    <div>客户诉求：{escape(detail.customer_request or '-')}</div>
  </div>
  <h3>服务项目</h3>
  <table>
    <thead><tr><th>项目</th><th>数量</th><th>单价</th><th>小计</th></tr></thead>
    <tbody>{item_rows or '<tr><td colspan="4">无</td></tr>'}</tbody>
  </table>
  <h3>配件</h3>
  <table>
    <thead><tr><th>配件</th><th>数量</th><th>单价</th><th>小计</th></tr></thead>
    <tbody>{part_rows or '<tr><td colspan="4">无</td></tr>'}</tbody>
  </table>
  <div class="total">
    合计：¥{detail.total_amount:.2f}<br/>
    折扣：¥{detail.discount_amount:.2f}<br/>
    应付：¥{detail.payable_amount:.2f}
    {'<br/>实付：¥' + f"{detail.paid_amount:.2f}" if doc_type == 'settle' else ''}
  </div>
  <div class="footer">
    <span>客户签字：____________</span>
    <span>服务顾问：____________</span>
  </div>
</body>
</html>"""
