import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from PIL import Image as PILImage

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to draw official MSG Letterhead header, footer,
    and page numbers on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        page_w, page_h = A4

        script_dir = os.path.dirname(os.path.abspath(__file__))
        header_path = os.path.join(script_dir, 'assets', 'msg_header.png')
        footer_path = os.path.join(script_dir, 'assets', 'msg_footer.png')

        # 1. Top Header Banner
        if os.path.exists(header_path):
            try:
                # Render exact extracted header banner
                self.drawImage(
                    header_path,
                    x=10 * mm,
                    y=page_h - 38 * mm,
                    width=page_w - 20 * mm,
                    height=32 * mm,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                print("Header draw warning:", e)

        # 2. Bottom Footer Banner
        if os.path.exists(footer_path):
            try:
                self.drawImage(
                    footer_path,
                    x=10 * mm,
                    y=6 * mm,
                    width=page_w - 20 * mm,
                    height=22 * mm,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                print("Footer draw warning:", e)
        else:
            # Fallback text footer if image missing
            footer_y = 12 * mm
            self.setStrokeColor(colors.HexColor("#003399"))
            self.setLineWidth(1.5)
            self.line(10 * mm, footer_y + 10 * mm, page_w - 10 * mm, footer_y + 10 * mm)

            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#333333"))
            
            contact_line = "☎ +971 4 295 1222    |    ✉ sales@msgoilfield.com    |    🌐 www.msgoilfield.com"
            address_line = "Dubai Industrial City Phase-1, Saih Shuaib 2, Warehouse No:J-04, Dubai, UAE."

            self.drawCentredString(page_w / 2.0, footer_y + 5 * mm, contact_line)
            self.drawCentredString(page_w / 2.0, footer_y + 1.5 * mm, address_line)

        # Page Number (bottom right margin)
        if page_count > 1:
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#666666"))
            self.drawRightString(page_w - 12 * mm, 4 * mm, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()


def get_image_dimensions(img_path, max_w, max_h):
    """Calculate proportional dimensions for ReportLab RLImage."""
    try:
        with PILImage.open(img_path) as im:
            w, h = im.size
            aspect = w / float(h)
            target_w = max_w
            target_h = max_w / aspect
            if target_h > max_h:
                target_h = max_h
                target_w = max_h * aspect
            return target_w, target_h
    except Exception:
        return max_w, max_h


def generate_loc_pdf(metadata, items, output_target):
    """
    Generates a Letter of Compliance (LOC) PDF based on exact MSG specifications.
    
    metadata: dict with keys: 'date', 'to_client', 'po_number', 'msg_ref', 'signatory_name', 'signatory_title'
    items: list of dicts with keys: 'sl_no', 'description', 'po_qty', 'uom', 'heat_number', 'remarks'
    output_target: file path string OR BytesIO stream
    """
    doc = SimpleDocTemplate(
        output_target,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=42 * mm,
        bottomMargin=30 * mm
    )

    page_w, _ = A4
    printable_w = page_w - (28 * mm) # ~515.8 pt

    styles = getSampleStyleSheet()

    # Typography styles
    hdr_label_style = ParagraphStyle(
        'HdrLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#000000')
    )

    title_style = ParagraphStyle(
        'LocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#000000'),
        alignment=1
    )

    body_style = ParagraphStyle(
        'LocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#1A1A1A')
    )

    tbl_hdr_style = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#000000'),
        alignment=1
    )

    tbl_cell_center = ParagraphStyle(
        'TblCellCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#000000'),
        alignment=1
    )

    tbl_cell_left = ParagraphStyle(
        'TblCellLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#000000'),
        alignment=0
    )

    sig_company_style = ParagraphStyle(
        'SigCompany',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#000000')
    )

    sig_name_style = ParagraphStyle(
        'SigName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#000000')
    )

    sig_title_style = ParagraphStyle(
        'SigTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#333333')
    )

    elements = []

    # 1. Header Metadata Section
    date_val = metadata.get('date', '')
    to_val = metadata.get('to_client', '')
    po_val = metadata.get('po_number', '')
    ref_val = metadata.get('msg_ref', '')

    hdr_text = (
        f"<b>Date:</b> {date_val}<br/>"
        f"<b>TO:</b> {to_val}<br/>"
        f"<b>PO Number:</b> {po_val}<br/>"
        f"<b>MSG Ref:</b> {ref_val}"
    )

    hdr_p = Paragraph(hdr_text, hdr_label_style)
    elements.append(hdr_p)
    elements.append(Spacer(1, 14))

    # 2. Document Title
    title_p = Paragraph("<u><b>LETTER OF COMPLIANCE</b></u>", title_style)
    elements.append(title_p)
    elements.append(Spacer(1, 14))

    # 3. Standard Compliance Declaration
    statement_text = (
        "We hereby confirm that below listed items have been fabricated as per the client PO requirements. "
        "Subsequent to the fabrication, dimensional verification and visual inspection were conducted, "
        "and the items are found to be acceptable and in full compliance with the applicable standards."
    )
    elements.append(Paragraph(statement_text, body_style))
    elements.append(Spacer(1, 14))

    # 4. Table Construction
    # Column Width Allocation (Total = printable_w = ~515.8 pt)
    col_w = [48, 180, 45, 40, 70, printable_w - (48 + 180 + 45 + 40 + 70)]

    table_data = [
        [
            Paragraph("<b>Sl.No</b>", tbl_hdr_style),
            Paragraph("<b>Description</b>", tbl_hdr_style),
            Paragraph("<b>PO Qty</b>", tbl_hdr_style),
            Paragraph("<b>UOM</b>", tbl_hdr_style),
            Paragraph("<b>Heat Number</b>", tbl_hdr_style),
            Paragraph("<b>Remarks</b>", tbl_hdr_style)
        ]
    ]

    for item in items:
        table_data.append([
            Paragraph(str(item.get('sl_no', '')), tbl_cell_center),
            Paragraph(str(item.get('description', '')), tbl_cell_left),
            Paragraph(str(item.get('po_qty', '')), tbl_cell_center),
            Paragraph(str(item.get('uom', '')), tbl_cell_center),
            Paragraph(str(item.get('heat_number', '')), tbl_cell_center),
            Paragraph(str(item.get('remarks', '')), tbl_cell_left)
        ])

    items_table = Table(table_data, colWidths=col_w, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.75, colors.HexColor('#000000')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FFFFFF')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))

    elements.append(items_table)
    elements.append(Spacer(1, 24))

    # 5. Signature Section
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sig_img_path = os.path.join(script_dir, 'assets', 'signature.png')
    stamp_img_path = os.path.join(script_dir, 'assets', 'stamp.png')

    sig_elements = []
    sig_elements.append(Paragraph("<b>For MSG Oilfield Equipment Trading,</b>", sig_company_style))
    sig_elements.append(Spacer(1, 6))

    has_sig = os.path.exists(sig_img_path)
    has_stamp = os.path.exists(stamp_img_path)

    if has_sig or has_stamp:
        sig_cells = []
        if has_sig:
            sw, sh = get_image_dimensions(sig_img_path, 110, 45)
            sig_cells.append(RLImage(sig_img_path, width=sw, height=sh))
        else:
            sig_cells.append(Paragraph("", body_style))

        if has_stamp:
            stw, sth = get_image_dimensions(stamp_img_path, 90, 55)
            sig_cells.append(RLImage(stamp_img_path, width=stw, height=sth))
        else:
            sig_cells.append(Paragraph("", body_style))

        graphics_table = Table([sig_cells], colWidths=[120, 120])
        graphics_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        sig_elements.append(graphics_table)
        sig_elements.append(Spacer(1, 4))
    else:
        sig_elements.append(Spacer(1, 35))

    sig_name = metadata.get('signatory_name', 'Pradeep Poojary')
    sig_title = metadata.get('signatory_title', '( QA / QC Dept )')

    sig_elements.append(Paragraph(f"<b>{sig_name}</b>", sig_name_style))
    sig_elements.append(Spacer(1, 2))
    sig_elements.append(Paragraph(sig_title, sig_title_style))

    elements.append(KeepTogether(sig_elements))

    doc.build(elements, canvasmaker=NumberedCanvas)
    return True
