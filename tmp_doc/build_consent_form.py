"""生成北京市窝沟封闭知情告知书空白模板。

行首对齐关键参数：
- 正文 12pt，一字宽 ≈ 12pt
- 满行 40 字 → 内容宽 16.933cm → 左右边距各 2.033cm
- 首行缩进 2 字 → 首行 38 字（与原图逐行一致）
切勿把边距改窄到 ~1.8cm（会变成约 41 字/行，行首错一位）。
"""
import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

OUT_BOTH = Path("/Users/zhouli/Desktop/北京市窝沟封闭项目知情告知书（正反面）_空白.docx")
OUT_FRONT = Path("/Users/zhouli/Desktop/北京市窝沟封闭项目知情告知书回执_空白.docx")
QR = Path("/Users/zhouli/data/code/chuangye/chexiu_bao/tmp_doc/qrcode_print.png")

FONT_SONG = "Songti SC"
FONT_KAI = "Kaiti SC"
FONT_HEI = "Heiti SC"

SIZE_BODY = Pt(12)
SIZE_TITLE = Pt(18)
SIZE_FOOTER = Pt(9)

# 40 字 × 12pt = 16.933cm；A4 21cm → 左右各 2.033cm
MARGIN_LR_CM = 2.033
MARGIN_TB = (1.6, 1.3)


def set_run_font(run, east_asia: str, size, bold: bool = False):
    run.font.size = size
    run.font.name = east_asia
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), east_asia)
    r_fonts.set(qn("w:hAnsi"), east_asia)
    r_fonts.set(qn("w:eastAsia"), east_asia)
    r_fonts.set(qn("w:cs"), east_asia)
    for child in list(r_pr):
        if child.tag.endswith("}b") or child.tag.endswith("}bCs"):
            r_pr.remove(child)
    if bold:
        for tag in ("w:b", "w:bCs"):
            r_pr.append(OxmlElement(tag))
    run.bold = bold


def add_para(
    text="",
    *,
    font=FONT_SONG,
    size=SIZE_BODY,
    bold=False,
    align=WD_ALIGN_PARAGRAPH.LEFT,
    indent=True,
    space_before=0,
    space_after=2,
    line_spacing=1.0,
):
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_before = Pt(space_before)
    fmt.space_after = Pt(space_after)
    fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    fmt.line_spacing = line_spacing
    p.alignment = align
    if indent:
        fmt.first_line_indent = Pt(size.pt * 2)
    else:
        fmt.first_line_indent = Pt(0)
    if text:
        set_run_font(p.add_run(text), font, size, bold)
    return p


def add_runs_para(
    runs,
    *,
    font=FONT_SONG,
    align=WD_ALIGN_PARAGRAPH.LEFT,
    indent=True,
    space_after=2,
    line_spacing=1.0,
):
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(space_after)
    fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    fmt.line_spacing = line_spacing
    p.alignment = align
    fmt.first_line_indent = Pt(SIZE_BODY.pt * 2) if indent else Pt(0)
    for text, bold in runs:
        if text:
            set_run_font(p.add_run(text), font, SIZE_BODY, bold)
    return p


def apply_page_grid(section):
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(MARGIN_TB[0])
    section.bottom_margin = Cm(MARGIN_TB[1])
    section.left_margin = Cm(MARGIN_LR_CM)
    section.right_margin = Cm(MARGIN_LR_CM)
    sect_pr = section._sectPr
    for child in list(sect_pr):
        if child.tag == qn("w:docGrid"):
            sect_pr.remove(child)
    # 仅行网格，避免字符网格与真实字体宽度冲突导致怪折行
    doc_grid = OxmlElement("w:docGrid")
    doc_grid.set(qn("w:type"), "lines")
    doc_grid.set(qn("w:linePitch"), "240")  # 12pt 单倍
    sect_pr.append(doc_grid)


def set_cell_border(cell, **kwargs):
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in list(tc_pr):
        if old.tag == qn("w:tcBorders"):
            tc_pr.remove(old)
    borders = OxmlElement("w:tcBorders")
    for edge, val in kwargs.items():
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val.get("val", "single"))
        el.set(qn("w:sz"), str(val.get("sz", 4)))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), val.get("color", "000000"))
        borders.append(el)
    tc_pr.append(borders)


def set_cell_margins(cell, top=40, bottom=40, left=60, right=60):
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in list(tc_pr):
        if old.tag == qn("w:tcMar"):
            tc_pr.remove(old)
    mar = OxmlElement("w:tcMar")
    for edge, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tc_pr.append(mar)


def nil_borders(cell):
    set_cell_border(
        cell,
        top={"val": "nil", "sz": 0},
        left={"val": "nil", "sz": 0},
        bottom={"val": "nil", "sz": 0},
        right={"val": "nil", "sz": 0},
    )


def add_page_break():
    p = doc.add_paragraph()
    run = p.add_run()
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    run._element.append(br)


def simulate_wrap(text: str, width: int = 40, indent: int = 2):
    lines, i, first = [], 0, True
    while i < len(text):
        cap = width - indent if first else width
        first = False
        lines.append(text[i : i + cap])
        i += cap
    return lines


def self_check():
    consent = (
        "我已充分理解“北京市免费窝沟封闭预防龋齿项目”内容及注意事项，"
        "同意（ ）或不同意（ ）"
        "（请在同意或不同意后打√，不同意则不需填写以下内容）"
        "我的孩子接受窝沟封闭预防龋齿服务并提供真实相关信息。"
    )
    intro = (
        "为最大限度保护未成年儿童的合法权益，北京市牙病防治所在为学龄儿童依法依规提供"
        "专业防龋工作的同时，请家长务必仔细阅读以下注意事项，并明确是否接受该防龋服务："
    )
    item2 = (
        "2、窝沟封闭预防儿童龋齿项目是一项系列工作，知情告知书只在首次对儿童进行窝沟封闭操作前由家长签署，"
        "如我们提供的服务内容无重大实质变化，在之后进行的窝沟封闭操作前不再重复告知。"
    )
    errors = []
    if "（  ）" in consent:
        errors.append("同意括号不能有两个空格")
    li = simulate_wrap(intro)
    if not li[0].endswith("提供") or not li[1].startswith("专业"):
        errors.append(f"intro 折行不对: {li}")
    l2 = simulate_wrap(item2)
    if not l2[0].endswith("窝沟") or not l2[1].startswith("封闭操作前"):
        errors.append(f"item2 折行不对: {l2}")
    lc = simulate_wrap(consent)
    if not lc[1].startswith("同意（ ）"):
        errors.append(f"consent 第2行首字不对: {lc}")
    tip = "关注微信公众号：点击公共卫生-免费防龋"
    tip_w = len(tip) * 9 / 72 * 2.54
    if tip_w > 8.0:
        errors.append(f"提示框第一行过宽 {tip_w:.2f}cm，会在框内折行")
    # 边距必须对应 40 字/行
    content = 21.0 - 2 * MARGIN_LR_CM
    chars = content / (12 / 72 * 2.54)
    if abs(chars - 40) > 0.15:
        errors.append(f"边距对应约 {chars:.2f} 字/行，必须是 40")
    if errors:
        raise SystemExit("自检失败:\n- " + "\n- ".join(errors))
    print(f"self_check ok (≈{chars:.2f} chars/line)")


def build_front():
    apply_page_grid(doc.sections[0])

    add_para(
        "北京市窝沟封闭项目知情告知书回执",
        font=FONT_HEI,
        size=SIZE_TITLE,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        indent=False,
        space_after=6,
        line_spacing=1.0,
    )

    add_para(
        "为最大限度保护未成年儿童的合法权益，北京市牙病防治所在为学龄儿童依法依规提供"
        "专业防龋工作的同时，请家长务必仔细阅读以下注意事项，并明确是否接受该防龋服务：",
        space_after=3,
    )

    # 1–4：楷体加粗 + 首行缩进 2 字（与原图一致）
    for text in (
        "1、本回执所填写的儿童及家长，包括：儿童姓名、性别、学校名称、所在班级及身份证号码，"
        "仅限于数据录入、核对、质量控制、寻访等工作所需。",
        "2、窝沟封闭预防儿童龋齿项目是一项系列工作，知情告知书只在首次对儿童进行窝沟封闭操作前由家长签署，"
        "如我们提供的服务内容无重大实质变化，在之后进行的窝沟封闭操作前不再重复告知。",
        "3、如果儿童转学，需请家长在儿童新入学后重新签署告知书。",
        "4、如果家长不同意您的孩子继续接受该项服务，请及时向学校保健医或医务人员说明。",
    ):
        add_para(text, font=FONT_KAI, bold=True, space_after=2)

    add_para(
        "如指定医疗机构提供入校服务，回执由学校保健医保存。如在医疗机构接受服务，该回执由医疗机构保存。",
        space_after=4,
    )

    add_para(
        "以下为家长填写栏目：",
        font=FONT_HEI,
        bold=True,
        indent=False,
        space_after=4,
        line_spacing=1.0,
    )

    add_runs_para(
        [
            ("我已充分理解“北京市免费窝沟封闭预防龋齿项目”内容及注意事项，", False),
            ("同意（ ）", True),
            ("或", False),
            ("不同意（ ）", True),
            ("（请在同意或不同意后打√，不同意则不需填写以下内容）", True),
            ("我的孩子接受窝沟封闭预防龋齿服务并提供真实相关信息。", False),
        ],
        space_after=4,
    )

    sp = "\u3000"
    add_para(
        f"儿童姓名：{sp*6}性别：{sp*4}身份证号码（外籍儿童需要提供护照号码）：",
        indent=False,
        space_after=4,
    )
    add_para(f"所在学校名称：{sp*14}所在班级：", indent=False, space_after=4)
    add_runs_para(
        [(f"家长签名：{sp*10}", False), ("（须为本人姓名 不得代签）", True)],
        indent=False,
        space_after=4,
    )
    add_para("电话：", indent=False, space_after=4)
    add_runs_para(
        [
            ("请注明与孩子关系：父 母 / 祖父母（外祖父母）/其他", False),
            ("（请准确注明）", True),
        ],
        indent=False,
        space_after=6,
    )

    # 日期 | 提示框 | 二维码 同行；提示框够宽保证第一行不折
    row = doc.add_table(rows=1, cols=2)
    row.autofit = False
    tbl = row._tbl
    tbl_pr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    if tbl.tblPr is None:
        tbl.insert(0, tbl_pr)
    for old in list(tbl_pr):
        if old.tag in (qn("w:tblW"), qn("w:tblLayout")):
            tbl_pr.remove(old)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), "9900")
    tw.set(qn("w:type"), "dxa")
    tbl_pr.append(tw)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)

    # 禁止表格跨页拆分被整表推到下页：允许行内拆分=false 但控制高度
    tr = row.rows[0]._tr
    tr_pr = tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    cant.set(qn("w:val"), "0")
    tr_pr.append(cant)

    left, right = row.rows[0].cells
    left.width = Cm(5.5)
    right.width = Cm(11.4)
    for cell in (left, right):
        nil_borders(cell)
        set_cell_margins(cell, top=0, bottom=0, left=0, right=40)

    lp = left.paragraphs[0]
    lp.paragraph_format.space_before = Pt(6)
    lp.paragraph_format.space_after = Pt(0)
    set_run_font(lp.add_run(f"日期：{sp*4}年{sp*3}月{sp*3}日"), FONT_SONG, SIZE_BODY, False)

    inner = right.add_table(rows=1, cols=2)
    tc = right._tc
    kids = [c for c in tc if c.tag != qn("w:tcPr")]
    if (
        len(kids) >= 2
        and kids[0].tag == qn("w:p")
        and kids[1].tag == qn("w:tbl")
        and not "".join(kids[0].itertext()).strip()
    ):
        tc.remove(kids[0])

    inner.autofit = False
    itbl = inner._tbl
    ipr = itbl.tblPr if itbl.tblPr is not None else OxmlElement("w:tblPr")
    if itbl.tblPr is None:
        itbl.insert(0, ipr)
    iw = OxmlElement("w:tblW")
    iw.set(qn("w:w"), "6600")
    iw.set(qn("w:type"), "dxa")
    ipr.append(iw)

    tip_cell, qr_cell = inner.rows[0].cells
    tip_cell.width = Cm(8.4)  # 9pt×19字≈6.0cm + 内边距，确保单行
    qr_cell.width = Cm(3.2)

    set_cell_border(
        tip_cell,
        top={"val": "single", "sz": 4},
        left={"val": "single", "sz": 4},
        bottom={"val": "single", "sz": 4},
        right={"val": "single", "sz": 4},
    )
    set_cell_margins(tip_cell, top=40, bottom=40, left=60, right=60)
    nil_borders(qr_cell)
    set_cell_margins(qr_cell, top=0, bottom=0, left=60, right=0)

    t1 = tip_cell.paragraphs[0]
    t1.paragraph_format.space_before = Pt(0)
    t1.paragraph_format.space_after = Pt(0)
    t1.paragraph_format.line_spacing = 1.0
    set_run_font(t1.add_run("关注微信公众号：点击公共卫生-免费防龋"), FONT_HEI, SIZE_FOOTER, False)
    t2 = tip_cell.add_paragraph()
    t2.paragraph_format.space_before = Pt(1)
    t2.paragraph_format.space_after = Pt(0)
    t2.paragraph_format.line_spacing = 1.0
    set_run_font(t2.add_run("可线上注册并查询服务结果"), FONT_HEI, SIZE_FOOTER, False)

    qp = qr_cell.paragraphs[0]
    qp.paragraph_format.space_before = Pt(0)
    qp.paragraph_format.space_after = Pt(0)
    if QR.exists():
        qp.add_run().add_picture(str(QR), width=Cm(2.4))


def build_back():
    add_page_break()
    add_para(
        "北京市窝沟封闭项目知情告知书",
        font=FONT_SONG,
        size=SIZE_TITLE,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        indent=False,
        space_after=8,
        line_spacing=1.0,
    )
    add_para("尊敬的学生家长（监护人）：", indent=False, space_after=4)
    for text in (
        "您好！口腔健康是全身健康的重要组成部分，为提高青少年口腔健康水平，减少龋齿发生，"
        "北京市政府为适龄儿童开展“免费窝沟封闭预防龋齿项目”，由本片区定点的指定医疗机构在规定时间内为您的孩子提供免费服务。"
        "为小学1-6年级学生每年进行一次口腔检查，对1-3年级符合适应证的第一恒磨牙进行窝沟封闭。"
        "不是所有的孩子和所有的第一恒磨牙都需要封闭，由医生检查确定。",
        "窝沟是牙齿表面凹凸不平的部位，由于其不易清洁且细菌食物残渣容易积聚在此发酵产酸腐蚀牙齿，"
        "因此成为最易发生龋齿的部位。调查显示，儿童90%以上的恒牙龋齿发生于磨牙的窝沟部位。"
        "窝沟封闭是世界卫生组织推荐的预防窝沟龋的有效措施，它是指在牙齿完全萌出后，在牙齿咬合面的窝沟上"
        "涂布一层高分子树脂材料（对人体无害），将发育中形成的深而狭窄的窝沟缝隙填补上，防止细菌和酸对牙齿的侵蚀，"
        "从而最大限度地减少龋齿发生。操作简便，无需磨牙。",
        "窝沟封闭可以最大限度地预防恒磨牙龋齿的发生，但并不意味着只要做了封闭孩子的牙齿就不会得龋齿。"
        "导致龋齿发生的因素很多，希望您继续帮助孩子做好口腔卫生维护，用含氟牙膏刷牙，少吃零食。"
        "如果您的孩子牙齿已经龋坏，应及时到正规医疗机构接受治疗（不属于免费公共卫生项目范畴）。",
        "为保证孩子顺利接受服务，请提供孩子的身份信息，包括：姓名、学校、班级、身份证号码等，"
        "个人基本信息只用于数据核对、质量控制、项目效果评价和管理等内容，不会外泄。"
        "由于相关操作、注意事项及风险等告知内容均相同，如无特殊情况，此次告知后将不再重复告知。"
        "本回执家长签署，如孩子转学或家长改变意见，请向校医或医务人员说明并重新签署。"
        "若家长带孩子到门诊接受服务，每次均需要填写知情同意书。回执由项目操作单位保存。",
    ):
        add_para(text, space_after=6, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY)


FONT_TABLE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:font w:name="Songti SC"><w:altName w:val="宋体"/><w:charset w:val="86"/><w:family w:val="roman"/><w:pitch w:val="variable"/></w:font>
  <w:font w:name="Kaiti SC"><w:altName w:val="楷体"/><w:charset w:val="86"/><w:family w:val="script"/><w:pitch w:val="variable"/></w:font>
  <w:font w:name="Heiti SC"><w:altName w:val="黑体"/><w:charset w:val="86"/><w:family w:val="swiss"/><w:pitch w:val="variable"/></w:font>
  <w:font w:name="宋体"><w:altName w:val="SimSun"/><w:charset w:val="86"/><w:family w:val="roman"/><w:pitch w:val="variable"/></w:font>
  <w:font w:name="楷体"><w:altName w:val="KaiTi"/><w:charset w:val="86"/><w:family w:val="script"/><w:pitch w:val="variable"/></w:font>
  <w:font w:name="黑体"><w:altName w:val="SimHei"/><w:charset w:val="86"/><w:family w:val="swiss"/><w:pitch w:val="variable"/></w:font>
</w:fonts>"""

SETTINGS_SNIPPET = (
    '\n  <w:themeFontLang w:val="en-US" w:eastAsia="zh-CN"/>'
    '\n  <w:characterSpacingControl w:val="compressPunctuation"/>'
    '\n'
)


def patch_fonts(path: Path):
    tmp = path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "word/fontTable.xml":
                continue
            data = zin.read(item.filename)
            if item.filename == "word/settings.xml" and "themeFontLang" not in data.decode():
                data = data.decode().replace("</w:settings>", SETTINGS_SNIPPET + "</w:settings>").encode()
            zout.writestr(item, data)
        zout.writestr("word/fontTable.xml", FONT_TABLE)
    shutil.move(tmp, path)


def save_doc(path: Path):
    doc.save(path)
    patch_fonts(path)
    print(f"saved: {path}")


def verify_front_only(path: Path):
    d = Document(path)
    page_breaks = 0
    for p in d.paragraphs:
        if p._element.xpath('.//*[local-name()="br"][@*[local-name()="type"]="page"]'):
            page_breaks += 1
    if page_breaks:
        raise SystemExit(f"{path.name} 不应有分页符，发现 {page_breaks} 个")
    # 条款加粗
    texts = ["".join(r.text for r in p.runs) for p in d.paragraphs]
    items = [t for t in texts if t.startswith(("1、", "2、", "3、", "4、"))]
    if len(items) < 4:
        raise SystemExit("缺少条款 1-4")
    for p in d.paragraphs:
        t = "".join(r.text for r in p.runs)
        if t.startswith("1、"):
            if not all(r.bold for r in p.runs if r.text):
                raise SystemExit("条款1未加粗")
    print(f"verify front-only ok: {path.name}")


def verify_both(path: Path):
    d = Document(path)
    brs = sum(
        1
        for p in d.paragraphs
        if p._element.xpath('.//*[local-name()="br"][@*[local-name()="type"]="page"]')
    )
    if brs != 1:
        raise SystemExit(f"{path.name} 应有 1 个分页，实际 {brs}")
    print(f"verify both ok: {path.name}")


self_check()

# —— 回执：仅正面，必须一页 ——
doc = Document()
apply_page_grid(doc.sections[0])
normal = doc.styles["Normal"]
normal.font.name = FONT_SONG
normal.font.size = SIZE_BODY
normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_SONG)
build_front()
save_doc(OUT_FRONT)
verify_front_only(OUT_FRONT)

# —— 正反面：正面 + 背面 ——
doc = Document()
apply_page_grid(doc.sections[0])
normal = doc.styles["Normal"]
normal.font.name = FONT_SONG
normal.font.size = SIZE_BODY
normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_SONG)
build_front()
build_back()
save_doc(OUT_BOTH)
verify_both(OUT_BOTH)
