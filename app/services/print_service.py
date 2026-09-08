from html import escape
from io import BytesIO

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

FUEL_MAP = {
    "empty": "空",
    "1/4": "1/4",
    "1/2": "1/2",
    "3/4": "3/4",
    "full": "满",
}

PDF_FONT = "STSong-Light"


def _vehicle_model_text(vehicle: Vehicle | None) -> str:
    if vehicle is None:
        return "-"
    text = f"{vehicle.brand or ''} {vehicle.model or ''}".strip()
    return text or "-"


class PrintService:
    @staticmethod
    def _build_context(db: Session, current_user: CurrentUser, order_id: int, doc_type: str) -> dict:
        if doc_type not in PRINT_TITLES:
            doc_type = "quote"

        detail = WorkOrderService.get_detail(db, current_user, order_id)
        store = db.query(Store).filter(Store.id == current_user.store_id).first()
        customer = db.query(Customer).filter(Customer.id == detail.customer_id).first()
        vehicle = db.query(Vehicle).filter(Vehicle.id == detail.vehicle_id).first()

        return {
            "doc_type": doc_type,
            "title": PRINT_TITLES[doc_type],
            "store_name": store.name if store else "车修宝",
            "detail": detail,
            "customer": customer,
            "vehicle": vehicle,
        }

    @staticmethod
    def render_html(db: Session, current_user: CurrentUser, order_id: int, doc_type: str) -> str:
        ctx = PrintService._build_context(db, current_user, order_id, doc_type)
        detail = ctx["detail"]
        customer = ctx["customer"]
        vehicle = ctx["vehicle"]
        store_name = escape(ctx["store_name"])
        title = ctx["title"]

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
    <div>车型：{escape(_vehicle_model_text(vehicle))}</div>
    <div>进店里程：{detail.mileage_in or '-'} km</div>
    <div>油量：{FUEL_MAP.get(detail.fuel_level or '', detail.fuel_level or '-')}</div>
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
    {'<br/>实付：¥' + f"{detail.paid_amount:.2f}" if ctx["doc_type"] == 'settle' else ''}
  </div>
  <div class="footer">
    <span>客户签字：____________</span>
    <span>服务顾问：____________</span>
  </div>
</body>
</html>"""

    @staticmethod
    def render_pdf(db: Session, current_user: CurrentUser, order_id: int, doc_type: str) -> bytes:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as exc:
            raise RuntimeError("PDF 导出需要安装 reportlab：pip install reportlab") from exc

        pdfmetrics.registerFont(UnicodeCIDFont(PDF_FONT))

        ctx = PrintService._build_context(db, current_user, order_id, doc_type)
        detail = ctx["detail"]
        customer = ctx["customer"]
        vehicle = ctx["vehicle"]

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
        title_style = ParagraphStyle("Title", fontName=PDF_FONT, fontSize=18, leading=22, alignment=1)
        sub_style = ParagraphStyle("Sub", fontName=PDF_FONT, fontSize=12, leading=16, alignment=1, textColor=colors.grey)
        normal = ParagraphStyle("Normal", fontName=PDF_FONT, fontSize=10, leading=14)
        section = ParagraphStyle("Section", fontName=PDF_FONT, fontSize=12, leading=16, spaceBefore=8, spaceAfter=4)

        story = [
            Paragraph(ctx["store_name"], title_style),
            Paragraph(ctx["title"], sub_style),
            Spacer(1, 8),
        ]

        meta_lines = [
            f"工单号：{detail.order_no}",
            f"状态：{detail.status_label}",
            f"客户：{customer.name if customer else '-'}",
            f"手机：{customer.phone if customer else '-'}",
            f"车牌：{vehicle.plate_number if vehicle else '-'}",
            f"车型：{_vehicle_model_text(vehicle)}",
            f"进店里程：{detail.mileage_in or '-'} km",
            f"油量：{FUEL_MAP.get(detail.fuel_level or '', detail.fuel_level or '-')}",
            f"开单时间：{detail.created_at}",
            f"客户诉求：{detail.customer_request or '-'}",
        ]
        for line in meta_lines:
            story.append(Paragraph(line, normal))
        story.append(Spacer(1, 10))

        story.append(Paragraph("服务项目", section))
        item_data = [["项目", "数量", "单价", "小计"]]
        for item in detail.items:
            item_data.append([item.name, str(item.quantity), f"¥{item.unit_price:.2f}", f"¥{item.amount:.2f}"])
        if len(item_data) == 1:
            item_data.append(["无", "", "", ""])
        story.append(PrintService._table(item_data, colors, mm, PDF_FONT))

        story.append(Paragraph("配件", section))
        part_data = [["配件", "数量", "单价", "小计"]]
        for part in detail.parts:
            part_data.append([part.name, str(part.quantity), f"¥{part.unit_price:.2f}", f"¥{part.amount:.2f}"])
        if len(part_data) == 1:
            part_data.append(["无", "", "", ""])
        story.append(PrintService._table(part_data, colors, mm, PDF_FONT))

        total_lines = [
            f"合计：¥{detail.total_amount:.2f}",
            f"折扣：¥{detail.discount_amount:.2f}",
            f"应付：¥{detail.payable_amount:.2f}",
        ]
        if ctx["doc_type"] == "settle":
            total_lines.append(f"实付：¥{detail.paid_amount:.2f}")
        story.append(Spacer(1, 8))
        for line in total_lines:
            story.append(Paragraph(line, ParagraphStyle("Total", fontName=PDF_FONT, fontSize=11, leading=15, alignment=2)))

        story.append(Spacer(1, 24))
        story.append(Paragraph("客户签字：____________　　　　　服务顾问：____________", normal))

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _table(data: list[list[str]], colors_module, mm_unit, font_name: str) -> "Table":
        from reportlab.platypus import Table, TableStyle

        table = Table(data, colWidths=[70 * mm_unit, 20 * mm_unit, 25 * mm_unit, 25 * mm_unit])
        table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, -1), font_name, 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors_module.HexColor("#f5f5f5")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors_module.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    @staticmethod
    def pdf_filename(order_no: str, doc_type: str) -> str:
        title = PRINT_TITLES.get(doc_type, "单据")
        return f"{order_no}_{title}.pdf"
