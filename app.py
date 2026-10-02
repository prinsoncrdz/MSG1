import os
import io
import argparse
import base64
import fitz # PyMuPDF
from flask import Flask, render_template, request, jsonify, send_file
from excel_parser import parse_excel_summary
from pdf_generator import generate_loc_pdf

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    include_all = request.form.get('include_all', 'false').lower() == 'true'

    try:
        data = parse_excel_summary(file, include_all=include_all)
        return jsonify({
            'success': True,
            'metadata': data['metadata'],
            'items': data['items']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def filter_loc_items(items, filter_empty_remarks=True):
    """Filter out items that do not have remarks if filter_empty_remarks is True."""
    if not filter_empty_remarks:
        return items
    return [it for it in items if it.get('remarks') and str(it.get('remarks')).strip()]

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    req_data = request.get_json()
    if not req_data:
        return jsonify({'success': False, 'error': 'Invalid request payload'}), 400

    metadata = req_data.get('metadata', {})
    items = req_data.get('items', [])
    filter_empty = req_data.get('filter_empty_remarks', True)

    filtered_items = filter_loc_items(items, filter_empty)

    if not filtered_items:
        return jsonify({
            'success': False,
            'error': 'No items with Remarks found. Letter of Compliance is only issued for modified materials with Remarks.'
        }), 400

    try:
        pdf_buffer = io.BytesIO()
        generate_loc_pdf(metadata, filtered_items, pdf_buffer)
        pdf_buffer.seek(0)
        
        filename = f"LOC_{metadata.get('po_number', 'Document')}.pdf".replace(' ', '_')
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/preview-pdf', methods=['POST'])
def preview_pdf():
    req_data = request.get_json()
    if not req_data:
        return jsonify({'success': False, 'error': 'Invalid request payload'}), 400

    metadata = req_data.get('metadata', {})
    items = req_data.get('items', [])
    filter_empty = req_data.get('filter_empty_remarks', True)

    filtered_items = filter_loc_items(items, filter_empty)

    if not filtered_items:
        return jsonify({
            'success': False,
            'error': 'No items with Remarks. Add remarks to include an item on the LOC PDF.'
        }), 400

    try:
        pdf_buffer = io.BytesIO()
        generate_loc_pdf(metadata, filtered_items, pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_imgs = []
        for i in range(len(doc)):
            pix = doc[i].get_pixmap(dpi=140)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
            page_imgs.append(f"data:image/png;base64,{img_b64}")

        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

        return jsonify({
            'success': True,
            'page_count': len(doc),
            'page_images': page_imgs,
            'item_count': len(filtered_items),
            'pdf_data': f"data:application/pdf;base64,{pdf_b64}"
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="LOC PDF Generator Web Server")
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5050)), help="Port to run the server on (default: 5050)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Host address (default: 0.0.0.0)")
    args = parser.parse_args()

    print(f"Starting LOC PDF Generator Server on http://localhost:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)
