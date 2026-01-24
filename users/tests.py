from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):
    """Tests for User model"""

    def test_create_user_with_default_role(self):
        """Test creating a user defaults to PARTICIPANT role"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.role, 'PARTICIPANT')
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')

    def test_create_user_with_admin_role(self):
        """Test creating a user with ADMIN role"""
        user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            role='ADMIN'
        )
        self.assertEqual(user.role, 'ADMIN')

    def test_user_string_representation(self):
        """Test user __str__ method"""
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='PARTICIPANT'
        )
        self.assertEqual(str(user), 'testuser (PARTICIPANT)')

    def test_role_choices(self):
        """Test valid role choices"""
        valid_roles = ['ADMIN', 'PARTICIPANT']
        for role in valid_roles:
            user = User.objects.create_user(
                username=f'user_{role}',
                password='testpass123',
                role=role
            )
            self.assertEqual(user.role, role)


class UserRegistrationTests(APITestCase):
    """Tests for user registration endpoint"""

    def setUp(self):
        self.register_url = '/api/users/register/'

    def test_register_participant_success(self):
        """Test successful participant registration"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'role': 'PARTICIPANT'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')
        self.assertEqual(user.role, 'PARTICIPANT')
        self.assertEqual(user.email, 'newuser@example.com')

    def test_register_admin_success(self):
        """Test successful admin registration"""
        data = {
            'username': 'newadmin',
            'email': 'newadmin@example.com',
            'password': 'securepass123',
            'role': 'ADMIN'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newadmin')
        self.assertEqual(user.role, 'ADMIN')

    def test_register_default_role(self):
        """Test registration without role defaults to PARTICIPANT"""
        data = {
            'username': 'defaultuser',
            'email': 'default@example.com',
            'password': 'securepass123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='defaultuser')
        self.assertEqual(user.role, 'PARTICIPANT')

    def test_register_duplicate_username(self):
        """Test registration with existing username fails"""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='testpass123'
        )
        data = {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password': 'securepass123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_username(self):
        """Test registration without username fails"""
        data = {
            'email': 'test@example.com',
            'password': 'securepass123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password(self):
        """Test registration without password fails"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_is_hashed(self):
        """Test that password is properly hashed"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepass123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='testuser')
        self.assertNotEqual(user.password, 'securepass123')
        self.assertTrue(user.check_password('securepass123'))


class UserLoginTests(APITestCase):
    """Tests for user login endpoint"""

    def setUp(self):
        self.login_url = '/api/users/login/'
        self.participant = User.objects.create_user(
            username='participant',
            email='participant@example.com',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            role='ADMIN'
        )

    def test_login_participant_success(self):
        """Test successful participant login"""
        data = {
            'username': 'participant',
            'password': 'participantpass'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['role'], 'PARTICIPANT')
        self.assertEqual(response.data['email'], 'participant@example.com')

    def test_login_admin_success(self):
        """Test successful admin login"""
        data = {
            'username': 'admin',
            'password': 'adminpass'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['role'], 'ADMIN')

    def test_login_returns_token(self):
        """Test login returns valid token"""
        data = {
            'username': 'participant',
            'password': 'participantpass'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify token exists in database
        token = Token.objects.get(key=response.data['token'])
        self.assertEqual(token.user, self.participant)

    def test_login_wrong_password(self):
        """Test login with wrong password fails"""
        data = {
            'username': 'participant',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        """Test login with non-existent user fails"""
        data = {
            'username': 'nonexistent',
            'password': 'somepassword'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_username(self):
        """Test login without username fails"""
        data = {
            'password': 'somepassword'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_password(self):
        """Test login without password fails"""
        data = {
            'username': 'participant'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multiple_logins_same_token(self):
        """Test multiple logins return same token"""
        data = {
            'username': 'participant',
            'password': 'participantpass'
        }
        response1 = self.client.post(self.login_url, data)
        response2 = self.client.post(self.login_url, data)
        self.assertEqual(response1.data['token'], response2.data['token'])


class UserSerializerTests(TestCase):
    """Tests for User serializers"""

    def test_user_serializer_fields(self):
        """Test UserSerializer includes correct fields"""
        from users.serializers import UserSerializer
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='PARTICIPANT'
        )
        serializer = UserSerializer(user)
        self.assertIn('id', serializer.data)
        self.assertIn('username', serializer.data)
        self.assertIn('email', serializer.data)
        self.assertIn('role', serializer.data)
        self.assertNotIn('password', serializer.data)

    def test_register_serializer_password_write_only(self):
        """Test RegisterSerializer password is write-only"""
        from users.serializers import RegisterSerializer
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 'PARTICIPANT'
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        # Password should not be in serializer output
        self.assertNotIn('password', RegisterSerializer(user).data)
