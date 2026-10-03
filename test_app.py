import unittest
import json
from app import app, DEFAULT_USER_EMAIL, STRONG_PASSWORD

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_login_flow(self):
        # 1. Accessing index unauthenticated redirects to /login
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

        # 2. Login with valid credentials
        login_res = self.app.post('/api/login', data=json.dumps({
            'email': DEFAULT_USER_EMAIL,
            'password': STRONG_PASSWORD
        }), content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(json.loads(login_res.data)['success'])

        # 3. Access index authenticated
        index_res = self.app.get('/')
        self.assertEqual(index_res.status_code, 200)
        self.assertIn(b'LETTER OF COMPLIANCE GENERATOR', index_res.data)

    def test_preview_pdf(self):
        # Log in first
        self.app.post('/api/login', data=json.dumps({
            'email': DEFAULT_USER_EMAIL,
            'password': STRONG_PASSWORD
        }), content_type='application/json')

        payload = {
            'metadata': {
                'date': '28/09/2026',
                'to_client': 'Test Client',
                'po_number': 'PO-12345',
                'msg_ref': 'MSG-REF-001',
                'signatory_name': 'Pradeep Poojary',
                'signatory_title': '( QA / QC Dept )',
                'action_type': 'fabricated'
            },
            'items': [
                {
                    'sl_no': '1',
                    'description': 'Test Valve SS316',
                    'po_qty': '10',
                    'uom': 'EA',
                    'heat_number': 'HT-100',
                    'remarks': 'MADE FROM PLATE THK. 25MM'
                }
            ]
        }
        response = self.app.post('/api/preview-pdf', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('page_images', data)

if __name__ == '__main__':
    unittest.main()
