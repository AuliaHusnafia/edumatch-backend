from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import User
from mentors.models import MentorProfile
from bookings.models import Booking


class MentorBookingsTests(APITestCase):
    def setUp(self):
        self.mentor_user = User.objects.create_user(
            username='mentor', email='mentor_t@example.com',
            password='password123', role='mentor', is_verified=True
        )
        self.mentor_profile = MentorProfile.objects.create(
            user=self.mentor_user, price_per_session=100000
        )
        self.mentee_user = User.objects.create_user(
            username='mentee', email='mentee_t@example.com',
            password='password123', role='mentee'
        )

    def test_list_mentors(self):
        """Daftar mentor terverifikasi harus muncul di endpoint publik"""
        url = reverse('list-mentors')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'mentor')

    def test_list_mentors_excludes_unverified(self):
        """Mentor yang belum diverifikasi admin tidak boleh muncul di daftar publik"""
        unverified = User.objects.create_user(
            username='mentor_baru', email='mentor_baru@example.com',
            password='password123', role='mentor', is_verified=False
        )
        MentorProfile.objects.create(user=unverified, price_per_session=50000)

        url = reverse('list-mentors')
        response = self.client.get(url)
        usernames = [m['username'] for m in response.data['results']]
        self.assertNotIn('mentor_baru', usernames)

    def test_book_mentor(self):
        """Mentee booking ke slot mingguan yang tersedia harus berhasil"""
        self.client.force_authenticate(user=self.mentee_user)
        # Format mingguan: pakai 'day', bukan 'date' spesifik
        self.mentor_profile.available_slots = [
            {'id': 'slot1', 'day': 'Senin', 'time': '10:00'}
        ]
        self.mentor_profile.save()

        url = reverse('book-mentor')
        data = {
            'mentor_id': self.mentor_user.id,
            'slot_id': 'slot1',
            'notes': 'Help me with Django'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Booking.objects.count(), 1)

        booking = Booking.objects.first()
        self.assertEqual(booking.mentor, self.mentor_user)
        self.assertEqual(booking.mentee, self.mentee_user)
        self.assertEqual(int(booking.invoice_amount), 100000)
        self.assertEqual(booking.status, 'pending')

    def test_book_mentor_invalid_slot(self):
        """Booking ke slot_id yang tidak ada harus ditolak"""
        self.client.force_authenticate(user=self.mentee_user)
        self.mentor_profile.available_slots = [
            {'id': 'slot1', 'day': 'Senin', 'time': '10:00'}
        ]
        self.mentor_profile.save()

        url = reverse('book-mentor')
        data = {
            'mentor_id': self.mentor_user.id,
            'slot_id': 'slot-tidak-ada',
            'notes': ''
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Booking.objects.count(), 0)

    def test_mentor_cannot_book_themselves(self):
        """Mentor tidak boleh booking dirinya sendiri lewat endpoint mentee"""
        self.client.force_authenticate(user=self.mentor_user)
        self.mentor_profile.available_slots = [
            {'id': 'slot1', 'day': 'Senin', 'time': '10:00'}
        ]
        self.mentor_profile.save()

        url = reverse('book-mentor')
        data = {
            'mentor_id': self.mentor_user.id,
            'slot_id': 'slot1',
            'notes': ''
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mentor_respond_booking_accept(self):
        """Mentor menerima booking harus mengubah status jadi accepted"""
        booking = Booking.objects.create(
            mentee=self.mentee_user,
            mentor=self.mentor_user,
            mentee_name=self.mentee_user.username,
            mentor_name=self.mentor_user.username,
            date='2025-12-01 10:00:00',
            status='pending'
        )
        self.client.force_authenticate(user=self.mentor_user)
        url = reverse('mentor-respond-booking')
        data = {'booking_id': booking.id, 'action': 'accept'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'accepted')

    def test_mentor_respond_booking_reject(self):
        """Mentor menolak booking harus mengubah status jadi rejected"""
        booking = Booking.objects.create(
            mentee=self.mentee_user,
            mentor=self.mentor_user,
            mentee_name=self.mentee_user.username,
            mentor_name=self.mentor_user.username,
            date='2025-12-01 10:00:00',
            status='pending'
        )
        self.client.force_authenticate(user=self.mentor_user)
        url = reverse('mentor-respond-booking')
        data = {'booking_id': booking.id, 'action': 'reject'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'rejected')

    def test_mentor_cannot_respond_to_others_booking(self):
        """Mentor lain (bukan pemilik booking) tidak boleh respond booking ini"""
        other_mentor = User.objects.create_user(
            username='mentor_lain', email='mentor_lain@example.com',
            password='password123', role='mentor', is_verified=True
        )
        booking = Booking.objects.create(
            mentee=self.mentee_user,
            mentor=self.mentor_user,
            mentee_name=self.mentee_user.username,
            mentor_name=self.mentor_user.username,
            date='2025-12-01 10:00:00',
            status='pending'
        )
        self.client.force_authenticate(user=other_mentor)
        url = reverse('mentor-respond-booking')
        data = {'booking_id': booking.id, 'action': 'accept'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'pending')  # tidak berubah

    def test_add_available_slot(self):
        """Mentor menambah jadwal mingguan baru harus tersimpan"""
        self.client.force_authenticate(user=self.mentor_user)
        url = reverse('mentor-available-slots')
        data = {'day': 'Rabu', 'time': '14:00'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mentor_profile.refresh_from_db()
        self.assertEqual(len(self.mentor_profile.available_slots), 1)
        self.assertEqual(self.mentor_profile.available_slots[0]['day'], 'Rabu')

    def test_add_duplicate_slot_rejected(self):
        """Menambah jadwal hari+waktu yang sudah ada harus ditolak"""
        self.mentor_profile.available_slots = [
            {'id': 'slot1', 'day': 'Senin', 'time': '09:00'}
        ]
        self.mentor_profile.save()

        self.client.force_authenticate(user=self.mentor_user)
        url = reverse('mentor-available-slots')
        data = {'day': 'Senin', 'time': '09:00'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_slot(self):
        """Mentor menghapus jadwal yang ada harus berhasil dan terhapus dari list"""
        self.mentor_profile.available_slots = [
            {'id': 'slot1', 'day': 'Senin', 'time': '09:00'},
            {'id': 'slot2', 'day': 'Selasa', 'time': '14:00'},
        ]
        self.mentor_profile.save()

        self.client.force_authenticate(user=self.mentor_user)
        url = reverse('mentor-delete-slot', kwargs={'slot_id': 'slot1'})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mentor_profile.refresh_from_db()
        self.assertEqual(len(self.mentor_profile.available_slots), 1)
        self.assertEqual(self.mentor_profile.available_slots[0]['id'], 'slot2')

    def test_mentee_cannot_access_mentor_only_endpoints(self):
        """Mentee tidak boleh akses endpoint khusus mentor (profile, slots, dll)"""
        self.client.force_authenticate(user=self.mentee_user)
        url = reverse('mentor-available-slots')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)