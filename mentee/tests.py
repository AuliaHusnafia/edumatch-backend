from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User
from mentors.models import MentorProfile
from bookings.models import Booking


class MenteeTests(APITestCase):
    def setUp(self):
        self.mentor_user = User.objects.create_user(
            username='mentor_a', email='mentor_a@example.com',
            password='password123', role='mentor', is_verified=True
        )
        self.mentor_profile = MentorProfile.objects.create(
            user=self.mentor_user,
            price_per_session=75000,
            skills='Python, Django',
            education='S1 Informatika',
            available_slots=[
                {'id': 'slot1', 'day': 'Senin', 'time': '10:00'},
                {'id': 'slot2', 'day': 'Rabu', 'time': '14:00'},
            ]
        )
        self.mentee_user = User.objects.create_user(
            username='mentee_a', email='mentee_a@example.com',
            password='password123', role='mentee'
        )

    # ── List & Detail Mentor ─────────────────────────────────────────────
    def test_list_mentors_public_access(self):
        """Daftar mentor harus bisa diakses tanpa login (publik)"""
        url = reverse('list-mentors')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_mentor_detail_shows_correct_data(self):
        """Detail mentor harus menampilkan data profil yang benar"""
        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('mentor-detail', kwargs={'mentor_id': self.mentor_user.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'mentor_a')
        self.assertEqual(response.data['price_per_session'], 75000)
        self.assertEqual(len(response.data['available_slots']), 2)

    def test_mentor_detail_not_found_for_unverified(self):
        """Mentor yang belum diverifikasi tidak boleh diakses detailnya"""
        unverified = User.objects.create_user(
            username='mentor_baru', email='mentor_baru@example.com',
            password='password123', role='mentor', is_verified=False
        )
        MentorProfile.objects.create(user=unverified, price_per_session=50000)

        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('mentor-detail', kwargs={'mentor_id': unverified.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Booking ──────────────────────────────────────────────────────────
    def test_book_mentor_success(self):
        """Mentee booking ke mentor dengan slot valid harus berhasil"""
        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('book-mentor')
        data = {
            'mentor_id': self.mentor_user.id,
            'slot_id': 'slot1',
            'notes': 'Mau belajar Django REST Framework'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(int(booking.invoice_amount), 75000)

    def test_book_mentor_requires_authentication(self):
        """Booking tanpa login harus ditolak"""
        url = reverse('book-mentor')
        data = {'mentor_id': self.mentor_user.id, 'slot_id': 'slot1', 'notes': ''}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_book_nonexistent_mentor(self):
        """Booking ke mentor_id yang tidak ada harus ditolak dengan rapi"""
        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('book-mentor')
        data = {'mentor_id': 99999, 'slot_id': 'slot1', 'notes': ''}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── My Bookings ──────────────────────────────────────────────────────
    def test_my_bookings_only_shows_own_bookings(self):
        """Mentee hanya boleh lihat booking miliknya sendiri, bukan punya mentee lain"""
        other_mentee = User.objects.create_user(
            username='mentee_lain', email='mentee_lain@example.com',
            password='password123', role='mentee'
        )
        Booking.objects.create(
            mentee=self.mentee_user, mentor=self.mentor_user,
            mentee_name=self.mentee_user.username, mentor_name=self.mentor_user.username,
            date='2025-12-01 10:00:00', status='pending'
        )
        Booking.objects.create(
            mentee=other_mentee, mentor=self.mentor_user,
            mentee_name=other_mentee.username, mentor_name=self.mentor_user.username,
            date='2025-12-02 10:00:00', status='pending'
        )

        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('my-bookings')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['mentor_name'], 'mentor_a')

    def test_my_bookings_empty_when_none(self):
        """Mentee yang belum pernah booking harus dapat list kosong, bukan error"""
        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('my-bookings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    # ── Ongoing & Completed Sessions ────────────────────────────────────
    def test_ongoing_sessions_shows_accepted_and_ongoing(self):
        """Endpoint ongoing-sessions harus menampilkan booking status accepted/ongoing saja"""
        Booking.objects.create(
            mentee=self.mentee_user, mentor=self.mentor_user,
            mentee_name=self.mentee_user.username, mentor_name=self.mentor_user.username,
            date='2025-12-01 10:00:00', status='accepted'
        )
        Booking.objects.create(
            mentee=self.mentee_user, mentor=self.mentor_user,
            mentee_name=self.mentee_user.username, mentor_name=self.mentor_user.username,
            date='2025-12-02 10:00:00', status='pending'  # tidak boleh muncul
        )

        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('mentee-ongoing-sessions')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = [b['status'] for b in response.data['results']]
        self.assertIn('accepted', statuses)
        self.assertNotIn('pending', statuses)

    def test_completed_sessions_includes_paid_and_completed(self):
        """Endpoint completed-sessions harus menampilkan status completed dan paid"""
        Booking.objects.create(
            mentee=self.mentee_user, mentor=self.mentor_user,
            mentee_name=self.mentee_user.username, mentor_name=self.mentor_user.username,
            date='2025-12-01 10:00:00', status='completed', invoice_amount=75000
        )
        Booking.objects.create(
            mentee=self.mentee_user, mentor=self.mentor_user,
            mentee_name=self.mentee_user.username, mentor_name=self.mentor_user.username,
            date='2025-12-02 10:00:00', status='paid', invoice_amount=75000
        )

        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('mentee-completed-sessions')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = [b['status'] for b in response.data['results']]
        self.assertIn('completed', statuses)
        self.assertIn('paid', statuses)

    def test_completed_sessions_shows_invoice_amount(self):
        """Tagihan di completed-sessions harus sesuai dengan harga sesi mentor"""
        Booking.objects.create(
            mentee=self.mentee_user, mentor=self.mentor_user,
            mentee_name=self.mentee_user.username, mentor_name=self.mentor_user.username,
            date='2025-12-01 10:00:00', status='completed', invoice_amount=75000
        )
        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('mentee-completed-sessions')
        response = self.client.get(url)

        self.assertEqual(int(response.data['results'][0]['invoice_amount']), 75000)

    def test_mentor_cannot_access_mentee_only_endpoints(self):
        """Mentor tidak boleh akses endpoint khusus mentee (my-bookings, dll)"""
        self.client.force_authenticate(user=self.mentor_user)
        url = reverse('my-bookings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)