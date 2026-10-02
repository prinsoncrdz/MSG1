import unittest
import json
import os
import io
from app import app

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Letter of Compliance (LOC) Generator', response.data)

    def test_preview_pdf(self):
        payload = {
            'metadata': {
                'date': '28/09/2026',
                'to_client': 'Test Client',
                'po_number': 'PO-12345',
                'msg_ref': 'MSG-REF-001',
                'signatory_name': 'Pradeep Poojary',
                'signatory_title': '( QA / QC Dept )'
            },
            'items': [
                {
                    'sl_no': '1',
                    'description': 'Test Valve SS316',
                    'po_qty': '10',
                    'uom': 'EA',
                    'heat_number': 'HT-100',
                    'remarks': 'TEST REMARK CLEAN'
                }
            ]
        }
        response = self.app.post('/api/preview-pdf', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('page_images', data)
        self.assertGreater(len(data['page_images']), 0)

    def test_generate_pdf(self):
        payload = {
            'metadata': {
                'date': '28/09/2026',
                'to_client': 'Test Client',
                'po_number': 'PO-12345',
                'msg_ref': 'MSG-REF-001'
            },
            'items': [
                {
                    'sl_no': '1',
                    'description': 'Test Item',
                    'po_qty': '5',
                    'uom': 'PCS',
                    'heat_number': 'H123',
                    'remarks': 'Remark sample'
                }
            ]
        }
        response = self.app.post('/api/generate-pdf', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')

if __name__ == '__main__':
    unittest.main()
