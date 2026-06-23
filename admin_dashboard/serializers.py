from rest_framework import serializers
from users.models import User
from bookings.models import Booking
from payments.models import Payment, WithdrawalRequest


class AdminUserSerializer(serializers.ModelSerializer):
    """Dipakai untuk PendingMentorsView, AllMentorsView, AllMenteesView"""
    date_joined = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'university', 'phone', 'date_joined']

    def get_date_joined(self, obj):
        return obj.date_joined.strftime('%Y-%m-%d')

    def get_university(self, obj):
        return obj.university or ''

    def get_phone(self, obj):
        return obj.phone or ''


class AdminBookingSerializer(serializers.ModelSerializer):
    """Dipakai untuk AllBookingsView — ambil invoice_amount asli dari Booking, bukan hardcode"""
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['id', 'mentee_name', 'mentor_name', 'date', 'status', 'invoice_amount', 'payment_status']

    def get_payment_status(self, obj):
        if obj.status == 'paid':
            return 'paid'
        if obj.status == 'completed':
            return 'pending'
        return '-'


class AdminPaymentSerializer(serializers.ModelSerializer):
    """Dipakai untuk AllPaymentsView — langsung dari model Payment asli, bukan dari Booking"""
    mentee_name = serializers.SerializerMethodField()
    mentor_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'order_id', 'mentee_name', 'mentor_name',
            'amount', 'platform_fee', 'mentor_revenue', 'status', 'paid_at'
        ]

    def get_mentee_name(self, obj):
        return obj.booking.mentee_name

    def get_mentor_name(self, obj):
        return obj.booking.mentor_name


class AdminTransactionSerializer(serializers.ModelSerializer):
    """Dipakai untuk TransactionsView — sama seperti Payment tapi format field beda (untuk kompatibilitas frontend lama)"""
    mentee = serializers.SerializerMethodField()
    mentor = serializers.SerializerMethodField()
    nominal = serializers.DecimalField(source='amount', max_digits=10, decimal_places=2)
    komisi = serializers.DecimalField(source='platform_fee', max_digits=10, decimal_places=2)
    mentor_dapat = serializers.DecimalField(source='mentor_revenue', max_digits=10, decimal_places=2)
    status = serializers.SerializerMethodField()
    waktu = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ['order_id', 'mentee', 'mentor', 'nominal', 'komisi', 'mentor_dapat', 'status', 'waktu']

    def get_mentee(self, obj):
        return obj.booking.mentee_name

    def get_mentor(self, obj):
        return obj.booking.mentor_name

    def get_status(self, obj):
        return 'Berhasil' if obj.status == 'success' else obj.get_status_display()

    def get_waktu(self, obj):
        if obj.paid_at:
            return obj.paid_at.strftime('%d/%m/%y, %H.%M')
        return '-'


class AdminWithdrawalSerializer(serializers.ModelSerializer):
    """Dipakai untuk WithdrawRequestsView"""
    mentor_name = serializers.SerializerMethodField()
    mentor_email = serializers.SerializerMethodField()
    amount = serializers.DecimalField(source='net_amount', max_digits=10, decimal_places=2)
    gross_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    admin_fee = serializers.DecimalField(source='admin_fee_deducted', max_digits=10, decimal_places=2)
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'mentor_name', 'mentor_email', 'amount', 'gross_amount', 'admin_fee',
            'bank_name', 'account_number', 'account_name', 'status', 'admin_note', 'created_at'
        ]

    def get_mentor_name(self, obj):
        return obj.mentor.username

    def get_mentor_email(self, obj):
        return obj.mentor.email

    def get_created_at(self, obj):
        return obj.created_at.strftime('%d %b %Y %H:%M')