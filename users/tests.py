from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User


class AuthTests(APITestCase):
    def test_register_mentee(self):
        url = reverse('register')
        data = {
            'username': 'testmentee',
            'email': 'mentee@example.com',
            'password': 'password123',
            'role': 'mentee',
            'university': 'Test University'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testmentee')
        self.assertTrue(User.objects.get().is_verified)

    def test_register_mentor(self):
        url = reverse('register')
        data = {
            'username': 'testmentor',
            'email': 'mentor@example.com',
            'password': 'password123',
            'role': 'mentor',
            'university': 'Test University'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(User.objects.get(username='testmentor').is_verified)

    def test_login(self):
        User.objects.create_user(username='testuser', password='password123', role='mentee')
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'password123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_get_me(self):
        user = User.objects.create_user(username='testuser', password='password123', role='mentee')
        self.client.force_authenticate(user=user)
        url = reverse('me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_register_duplicate_email(self):
        """Registrasi dengan email yang sudah dipakai harus ditolak"""
        User.objects.create_user(
            username='existing', email='dup@example.com',
            password='password123', role='mentee'
        )
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'dup@example.com',
            'password': 'password123',
            'role': 'mentee',
            'university': 'Test University'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """Registrasi dengan username yang sudah dipakai harus ditolak"""
        User.objects.create_user(
            username='dupuser', email='first@example.com',
            password='password123', role='mentee'
        )
        url = reverse('register')
        data = {
            'username': 'dupuser',
            'email': 'second@example.com',
            'password': 'password123',
            'role': 'mentee',
            'university': 'Test University'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_wrong_password(self):
        """Login dengan password salah harus ditolak"""
        User.objects.create_user(username='testuser', password='password123', role='mentee')
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'passwordsalah'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        """Login dengan username yang tidak terdaftar harus ditolak"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'usertidakada',
            'password': 'password123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_me_without_authentication(self):
        """Akses /auth/me/ tanpa login (tanpa token) harus ditolak"""
        url = reverse('me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)