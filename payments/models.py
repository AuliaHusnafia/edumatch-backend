from django.db import models
from users.models import User
from bookings.models import Booking


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Menunggu Pembayaran'),
        ('success', 'Berhasil'),
        ('failed', 'Gagal'),
    )

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name='payment'
    )
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Fee breakdown — dihitung saat payment dibuat, bukan saat withdraw
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mentor_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_link = models.URLField(blank=True, null=True)
    snap_token = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.order_id} - {self.status}"


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Menunggu Persetujuan'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    )

    mentor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='withdrawals'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Simpan breakdown yang jelas
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    admin_fee_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=50, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    admin_note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Withdrawal {self.mentor.username} - Rp {self.net_amount}"