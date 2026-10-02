import os
import openpyxl
import fitz # PyMuPDF
from loc_pdf_generator import build_loc_pdf

def create_sample_excel(filepath):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Materials"
    
    headers = [
        "SL NO", "Description", "PO Qty", "UOM", "Heat Number",
        "Certificate Number", "MAKE", "Remarks-1", "Remarks-2",
        "Supplier", "PO Number"
    ]
    ws.append(headers)
    
    sample_rows = [
        (1, '3/4" High Pressure Ball Valve SS316 6000 PSI', 50, 'PCS', 'HT-884920', 'CERT-2024-0012', 'SWAGELOK', 'LOC: BAY-01 / RACK-A3', 'BIN-14', 'Global Oilfield Supplies FZE', 'PO-99481'),
        (2, 'Seamless Carbon Steel Pipe 2" Sch 80 API 5L Gr. B', 120, 'MTR', 'H-99214A', 'EN10204-3.1-992', 'TENARIS', 'YARD-B / SECTION-4', 'YARD-B / SECTION-4', 'Tubular Solutions Ltd', 'PO-99482'),
        (3, 'Flange WN 4" 150# RTJ A105 NACE MR0175', 25, 'PCS', 'HT-77412', 'MTC-2024-551', 'KROEPLIN', 'LOC: RACK-C2', None, 'MSG Piping Components', 'PO-99485'),
        (4, 'Stud Bolts with 2 Heavy Hex Nuts 7/8" x 5-1/2" B7/2H', 500, 'SET', 'B7-44910', 'CERT-884-11', 'FASTENAL', None, None, 'Fastener World FZCO', 'PO-99488'),
        (5, 'Gasket Spiral Wound 6" 300# Inner & Outer Ring SS316/FG', 80, 'PCS', 'GSK-2024-9', 'MTC-99120', 'FLEXITALLIC', 'WH-02 SHELF-05', 'BOX-A', 'Sealing Tech Trading', 'PO-99490')
    ]
    
    for row in sample_rows:
        ws.append(row)
        
    wb.save(filepath)
    print(f"Sample Excel created at: {filepath}")

def convert_pdf_to_images(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    img_paths = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        img_name = f"page_{page_idx + 1}.png"
        img_path = os.path.join(output_dir, img_name)
        pix.save(img_path)
        img_paths.append(img_path)
        print(f"Rendered PDF page {page_idx + 1} to image: {img_path}")
    return img_paths

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'sample_materials.xlsx')
    logo_path = os.path.join(base_dir, 'logo.png')
    sig_path = os.path.join(base_dir, 'sample_signature.png')
    pdf_out = os.path.join(base_dir, 'material_loc_labels_a4.pdf')

    create_sample_excel(excel_path)

    success = build_loc_pdf(excel_path, logo_path, sig_path, pdf_out)
    if success:
        imgs = convert_pdf_to_images(pdf_out, base_dir)
        print("PDF Generation and Conversion complete!")

if __name__ == '__main__':
    main()
