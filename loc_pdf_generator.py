import os
import re
import argparse
import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from PIL import Image as PILImage

def parse_loc_from_remarks(rem1, rem2):
    """
    Extracts, cleans, deduplicates, and combines LOC / Location information
    from Remarks-1 and Remarks-2.
    """
    candidates = []
    for r in [rem1, rem2]:
        if r is None:
            continue
        val = str(r).strip()
        if not val or val.upper() in ['NONE', 'NAN', 'N/A', '-', '']:
            continue
        
        # Strip prefixes like LOC:, LOCATION:, LOC -, LOCATION -
        cleaned = val
        match = re.search(r'(?:LOC|LOCATION)\s*[:=\-]\s*(.*)', val, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        
        if cleaned and cleaned not in candidates:
            # Check for duplicate entries (case-insensitive)
            is_dup = False
            for existing in candidates:
                if cleaned.upper() == existing.upper():
                    is_dup = True
                    break
            if not is_dup:
                candidates.append(cleaned)
    
    if not candidates:
        return "LOC: NOT FOUND"
    
    # Combine candidate locations with clear divider
    combined = " / ".join(candidates)
    return combined

def read_excel_data(excel_path):
    """
    Reads all rows from the Excel file and extracts required columns.
    Expected columns:
    SL NO, Description, PO Qty, UOM, Heat Number, Certificate Number,
    MAKE, Remarks-1, Remarks-2, Supplier, PO Number
    """
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active
    
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    
    # Locate header row dynamically
    header_idx = 0
    headers = []
    for idx, row in enumerate(rows[:10]):
        if row and any(k for k in row if k and 'DESCRIPTION' in str(k).upper()):
            header_idx = idx
            headers = [str(cell).strip() if cell is not None else '' for cell in row]
            break
    
    if not headers and rows:
        headers = [str(cell).strip() if cell is not None else '' for cell in rows[0]]
        header_idx = 0

    def find_col(possible_names):
        for name in possible_names:
            for i, h in enumerate(headers):
                clean_h = re.sub(r'[^A-ZA-Z0-9]', '', h.upper())
                clean_target = re.sub(r'[^A-ZA-Z0-9]', '', name.upper())
                if clean_target in clean_h or clean_h == clean_target:
                    return i
        return -1

    col_sl = find_col(['SL NO', 'SLNO', 'SL.NO', 'S.NO', 'SERIAL', 'NO'])
    col_desc = find_col(['Description', 'Desc', 'Item Description'])
    col_po_qty = find_col(['PO Qty', 'PO Quantity', 'Qty'])
    col_uom = find_col(['UOM', 'Unit'])
    col_heat = find_col(['Heat Number', 'Heat No', 'Heat#'])
    col_cert = find_col(['Certificate Number', 'Certificate No', 'Cert No'])
    col_make = find_col(['MAKE', 'Manufacturer', 'Brand'])
    col_rem1 = find_col(['Remarks-1', 'Remarks 1', 'Remark1', 'Remarks'])
    col_rem2 = find_col(['Remarks-2', 'Remarks 2', 'Remark2'])
    col_supp = find_col(['Supplier', 'Vendor'])
    col_po = find_col(['PO Number', 'PO No', 'PO#', 'Purchase Order'])

    data_rows = []
    for row in rows[header_idx + 1:]:
        if not row or all(c is None or str(c).strip() == '' for c in row):
            continue
        
        def get_val(idx):
            if idx != -1 and idx < len(row):
                v = row[idx]
                return str(v).strip() if v is not None else ''
            return ''

        sl_raw = get_val(col_sl)
        try:
            sl_num = int(float(sl_raw))
        except (ValueError, TypeError):
            sl_num = 999999

        rem1 = get_val(col_rem1)
        rem2 = get_val(col_rem2)
        loc_val = parse_loc_from_remarks(rem1, rem2)

        item = {
            'sl_no': sl_raw if sl_raw else str(len(data_rows) + 1),
            'sl_num': sl_num,
            'description': get_val(col_desc) or '-',
            'po_qty': get_val(col_po_qty) or '-',
            'uom': get_val(col_uom) or '',
            'heat_number': get_val(col_heat) or '-',
            'certificate_number': get_val(col_cert) or '-',
            'make': get_val(col_make) or '-',
            'remarks_1': rem1,
            'remarks_2': rem2,
            'supplier': get_val(col_supp) or '-',
            'po_number': get_val(col_po) or '-',
            'loc': loc_val
        }
        data_rows.append(item)

    # Sort strictly according to SL NO
    data_rows.sort(key=lambda x: (x['sl_num'], x['sl_no']))
    return data_rows

def get_image_dims(img_path, max_w, max_h):
    """Calculates proportional width and height for ReportLab RLImage."""
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
    except Exception as e:
        print(f"Warning: Could not open image {img_path}: {e}")
        return max_w, max_h

def build_loc_pdf(excel_path, logo_path, signature_path, output_pdf_path):
    """
    Generates a print-ready A4 PDF containing 2 material location tags per page.
    """
    data_items = read_excel_data(excel_path)
    if not data_items:
        print(f"Error: No valid data items found in {excel_path}")
        return False

    # A4 Page Setup (210mm x 297mm)
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    page_w, page_h = A4
    printable_w = page_w - (28 * mm) # ~515.8 pt
    tag_width = printable_w
    inner_w = tag_width - 10 # Width inside container borders

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )

    ref_style = ParagraphStyle(
        'RefTag',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
        alignment=2
    )

    loc_hdr_style = ParagraphStyle(
        'LocHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )

    loc_val_style = ParagraphStyle(
        'LocVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )

    loc_val_not_found_style = ParagraphStyle(
        'LocValNotFound',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16.5,
        leading=20,
        textColor=colors.HexColor('#DC2626'),
        alignment=1
    )

    cell_label_style = ParagraphStyle(
        'CellLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#334155')
    )

    cell_val_style = ParagraphStyle(
        'CellVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )

    cell_val_bold = ParagraphStyle(
        'CellValBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )

    sig_label_style = ParagraphStyle(
        'SigLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B'),
        alignment=0
    )

    elements = []

    for idx, item in enumerate(data_items):
        # 1. Header Section: Logo, Document Title, SL NO Reference
        logo_w, logo_h = get_image_dims(logo_path, 125, 36)
        logo_img = RLImage(logo_path, width=logo_w, height=logo_h)
        logo_img.hAlign = 'LEFT'

        header_title_p = Paragraph(
            "<b>MATERIAL LOCATION / LOC</b><br/>"
            "<font size=7.5 color='#475569'>MSG OILFIELD SUPPLIES</font>",
            title_style
        )
        
        ref_p = Paragraph(
            f"<b>SL NO: {item['sl_no']}</b><br/>"
            f"<font size=7 color='#64748B'>REF #{str(item['sl_no']).zfill(4) if str(item['sl_no']).isdigit() else str(item['sl_no'])}</font>",
            ref_style
        )

        header_table = Table(
            [[logo_img, header_title_p, ref_p]],
            colWidths=[125, inner_w - 245, 120],
            rowHeights=[38]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))

        # 2. LOC Display Box
        is_not_found = "NOT FOUND" in item['loc'].upper()
        current_loc_style = loc_val_not_found_style if is_not_found else loc_val_style

        loc_hdr_p = Paragraph("LOCATION / LOC", loc_hdr_style)
        loc_val_p = Paragraph(f"<b>{item['loc']}</b>", current_loc_style)

        loc_box_table = Table(
            [[loc_hdr_p], [loc_val_p]],
            colWidths=[inner_w],
            rowHeights=[14, 28]
        )

        loc_bg_color = colors.HexColor('#FEF2F2') if is_not_found else colors.HexColor('#F8FAFC')
        loc_border_color = colors.HexColor('#FCA5A5') if is_not_found else colors.HexColor('#CBD5E1')

        loc_box_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), loc_bg_color),
            ('BOX', (0,0), (-1,-1), 1, loc_border_color),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))

        # 3. Data Specification Table
        w_l1, w_v1, w_l2, w_v2 = 80, (inner_w - 160) / 2, 80, (inner_w - 160) / 2

        spec_data = [
            [
                Paragraph("Description:", cell_label_style),
                Paragraph(item['description'], cell_val_bold),
                Paragraph("PO Number:", cell_label_style),
                Paragraph(item['po_number'], cell_val_bold)
            ],
            [
                Paragraph("PO Qty & UOM:", cell_label_style),
                Paragraph(f"{item['po_qty']} {item['uom']}".strip(), cell_val_style),
                Paragraph("MAKE:", cell_label_style),
                Paragraph(item['make'], cell_val_style)
            ],
            [
                Paragraph("Heat Number:", cell_label_style),
                Paragraph(item['heat_number'], cell_val_style),
                Paragraph("Certificate No:", cell_label_style),
                Paragraph(item['certificate_number'], cell_val_style)
            ],
            [
                Paragraph("Supplier:", cell_label_style),
                Paragraph(item['supplier'], cell_val_style),
                Paragraph("Remarks (1 & 2):", cell_label_style),
                Paragraph(f"{item['remarks_1'] or '-'} | {item['remarks_2'] or '-'}", cell_val_style)
            ]
        ]

        spec_table = Table(
            spec_data,
            colWidths=[w_l1, w_v1, w_l2, w_v2]
        )
        spec_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
            ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F8FAFC')),
            ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFFFFF')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))

        # 4. Signature Section
        sig_w, sig_h = get_image_dims(signature_path, 110, 28)
        sig_img = RLImage(signature_path, width=sig_w, height=sig_h)
        sig_img.hAlign = 'LEFT'

        sig_title_p = Paragraph("<b>Authorized Signature</b>", sig_label_style)
        auth_by_p = Paragraph("<b>Authorized By:</b> ____________________", cell_label_style)
        date_p = Paragraph("<b>Date:</b> ____________________", cell_label_style)

        sig_table_data = [
            [sig_title_p, auth_by_p, date_p],
            [sig_img, Paragraph("", cell_label_style), Paragraph("", cell_label_style)]
        ]

        sig_table = Table(
            sig_table_data,
            colWidths=[140, 160, inner_w - 300]
        )
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('ALIGN', (2,0), (2,-1), 'LEFT'),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor('#CBD5E1')), # Top border for signature section
        ]))

        # 5. Build Tag Outer Container
        tag_content = [
            header_table,
            Spacer(1, 4),
            loc_box_table,
            Spacer(1, 5),
            spec_table,
            Spacer(1, 6),
            sig_table
        ]

        tag_container_table = Table(
            [[c] for c in tag_content],
            colWidths=[tag_width]
        )
        tag_container_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')), # Primary Navy outer border
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ]))

        elements.append(tag_container_table)
        
        # Add page layout breaks/spacing
        if idx % 2 == 0 and idx < len(data_items) - 1:
            elements.append(Spacer(1, 10 * mm)) # Vertical gap between 2 tags on the same page
        elif idx % 2 == 1 and idx < len(data_items) - 1:
            elements.append(PageBreak()) # New A4 page

    doc.build(elements)
    print(f"Successfully generated print-ready PDF: {output_pdf_path}")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate A4 Material Location (LOC) PDF tags from Excel.")
    parser.add_argument('--excel', help="Path to input Excel file", default='sample_materials.xlsx')
    parser.add_argument('--logo', help="Path to company logo PNG image", default='logo.png')
    parser.add_argument('--signature', help="Path to authorized signature PNG image", default='sample_signature.png')
    parser.add_argument('--output', help="Path for output PDF file", default='material_loc_labels_a4.pdf')
    
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    def resolve_path(p):
        return p if os.path.isabs(p) else os.path.join(script_dir, p)

    excel_file = resolve_path(args.excel)
    logo_file = resolve_path(args.logo)
    sig_file = resolve_path(args.signature)
    out_pdf = resolve_path(args.output)

    if os.path.exists(excel_file):
        build_loc_pdf(excel_file, logo_file, sig_file, out_pdf)
    else:
        print(f"Excel file not found: {excel_file}")
