from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from bookings.models import Booking
from decimal import Decimal
import uuid

User = get_user_model()


class PaymentTests(APITestCase):
    def setUp(self):
        self.mentee = User.objects.create_user(
            username='mentee_test', email='mentee_test@example.com',
            password='password123', role='mentee'
        )
        self.mentor = User.objects.create_user(
            username='mentor_test', email='mentor_test@example.com',
            password='password123', role='mentor'
        )
        self.booking = Booking.objects.create(
            mentee=self.mentee,
            mentor=self.mentor,
            mentee_name='mentee_test',
            mentor_name='mentor_test',
            date='2025-12-01 10:00:00',
            status='completed',
            invoice_amount=Decimal('100000.00')
        )
        self.client.login(username='mentee_test', password='password123')
        response = self.client.post(reverse('token_obtain_pair'), {'username': 'mentee_test', 'password': 'password123'})
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_create_payment_session(self):
        url = reverse('create-payment')
        data = {'booking_id': self.booking.id}
        response = self.client.post(url, data, format='json')

        if response.status_code == 200:
            self.assertIn('token', response.data)
            self.assertIn('redirect_url', response.data)
        else:
            self.assertNotEqual(response.status_code, 404)
            self.assertNotEqual(response.status_code, 403)

    def test_mentor_earnings_access(self):
        url = reverse('mentor-earnings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username='mentor_test', password='password123')
        response = self.client.post(reverse('token_obtain_pair'), {'username': 'mentor_test', 'password': 'password123'})
        mentor_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + mentor_token)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('total', response.data)

    def _login_as(self, username, password='password123'):
        """Helper: login dan pasang token ke header request"""
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': username, 'password': password}
        )
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

    def _make_successful_payment(self, booking, mentor_revenue=Decimal('90000')):
        """Helper: buat record Payment sukses langsung di database (tanpa lewat Midtrans)"""
        from payments.models import Payment
        return Payment.objects.create(
            booking=booking,
            order_id=f"TEST-{booking.id}-{uuid.uuid4().hex[:6].upper()}",
            amount=Decimal('100000'),
            platform_fee=Decimal('10000'),
            mentor_revenue=mentor_revenue,
            status='success',
        )

    def test_mentor_earnings_calculation(self):
        """Pendapatan mentor harus dihitung benar dari payment yang sukses"""
        self._make_successful_payment(self.booking, mentor_revenue=Decimal('90000'))

        self._login_as('mentor_test')
        url = reverse('mentor-earnings')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 90000)
        self.assertEqual(response.data['available_balance'], 90000)
        self.assertEqual(response.data['total_withdrawn'], 0)

    def test_withdrawal_request_success(self):
        """Mentor dengan saldo cukup harus bisa mengajukan pencairan"""
        self._make_successful_payment(self.booking, mentor_revenue=Decimal('90000'))

        self._login_as('mentor_test')
        url = reverse('request-withdrawal')
        data = {
            'amount': '50000',
            'bank_name': 'BCA',
            'account_number': '1234567890',
            'account_name': 'Mentor Test'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('withdrawal_id', response.data)
        self.assertEqual(response.data['net_amount'], 50000)

    def test_withdrawal_request_insufficient_balance(self):
        """Mentor tidak boleh mencairkan lebih dari saldo yang tersedia"""
        self._make_successful_payment(self.booking, mentor_revenue=Decimal('90000'))

        self._login_as('mentor_test')
        url = reverse('request-withdrawal')
        data = {
            'amount': '999999',
            'bank_name': 'BCA',
            'account_number': '1234567890',
            'account_name': 'Mentor Test'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Saldo tidak cukup', response.data['error'])

    def test_withdrawal_below_minimum(self):
        """Pencairan di bawah Rp 50.000 harus ditolak"""
        self._make_successful_payment(self.booking, mentor_revenue=Decimal('90000'))

        self._login_as('mentor_test')
        url = reverse('request-withdrawal')
        data = {
            'amount': '10000',
            'bank_name': 'BCA',
            'account_number': '1234567890',
            'account_name': 'Mentor Test'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Minimal pencairan', response.data['error'])

    def test_withdrawal_mentee_cannot_access(self):
        """Mentee (bukan mentor) tidak boleh mengajukan pencairan"""
        self._login_as('mentee_test')
        url = reverse('request-withdrawal')
        data = {'amount': '50000', 'bank_name': 'BCA', 'account_number': '123', 'account_name': 'Test'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_balance_decreases_after_approved_withdrawal(self):
        """Saldo tersedia harus berkurang setelah withdrawal di-approve admin"""
        from payments.models import WithdrawalRequest
        self._make_successful_payment(self.booking, mentor_revenue=Decimal('90000'))

        WithdrawalRequest.objects.create(
            mentor=self.mentor,
            amount=Decimal('40000'),
            gross_amount=Decimal('40000'),
            net_amount=Decimal('40000'),
            status='approved',
        )

        self._login_as('mentor_test')
        url = reverse('mentor-earnings')
        response = self.client.get(url)

        self.assertEqual(response.data['total'], 90000)
        self.assertEqual(response.data['total_withdrawn'], 40000)
        self.assertEqual(response.data['available_balance'], 50000)

    def test_simulate_payment_success_updates_booking_status(self):
        """Endpoint simulate-success harus mengubah status booking jadi paid."""
        self._login_as('mentee_test')
        url = reverse('simulate-success')
        data = {'booking_id': self.booking.id}

        with override_settings(DEBUG=True):
            response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'paid')

    def test_simulate_payment_success_blocked_when_debug_false(self):
        """Endpoint simulate-success harus diblokir saat DEBUG=False (perilaku production)"""
        self._login_as('mentee_test')
        url = reverse('simulate-success')
        data = {'booking_id': self.booking.id}

        with override_settings(DEBUG=False):
            response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)