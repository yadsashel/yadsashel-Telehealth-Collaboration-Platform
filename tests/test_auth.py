# tests/test_auth.py
import unittest
from app import app, SQLASession
from models import User
from werkzeug.security import generate_password_hash

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Create test user
        with SQLASession() as session:
            self.test_email = "testuser@example.com"
            existing = session.query(User).filter_by(email=self.test_email).first()
            if existing:
                session.delete(existing)
                session.commit()

            test_user = User(
                user_type="patient",
                first_name="Test",
                last_name="User",
                email=self.test_email,
                tel="1234567890",
                password=generate_password_hash("password123"),
                sc_code="1234",
                image_url=""
            )
            session.add(test_user)
            session.commit()

    def tearDown(self):
        # Remove test user
        with SQLASession() as session:
            user = session.query(User).filter_by(email=self.test_email).first()
            if user:
                session.delete(user)
                session.commit()

    def test_login_success(self):
        response = self.app.post('/login', data={
            'user_type': 'patient',
            'first_name': 'Test',
            'password': 'password123',
            'sc_code': '1234'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'patient', response.data)  # Checks redirection worked

    def test_login_failure_wrong_password(self):
        response = self.app.post('/login', data={
            'user_type': 'patient',
            'first_name': 'Test',
            'password': 'wrongpass',
            'sc_code': '1234'
        }, follow_redirects=True)

        self.assertIn(b'Invalid credentials', response.data)

if __name__ == '__main__':
    unittest.main()