import uuid
import hashlib
import midtransclient
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics

from bookings.models import Booking
from mentors.models import MentorProfile
from .models import Payment, WithdrawalRequest
from .serializers import WithdrawalHistorySerializer


PLATFORM_FEE_PCT = Decimal('0.10')

snap = midtransclient.Snap(
    is_production=settings.MIDTRANS_IS_PRODUCTION,
    server_key=settings.MIDTRANS_SERVER_KEY,
    client_key=settings.MIDTRANS_CLIENT_KEY,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment(request):
    """Mentee membuat tagihan — FIX: hapus pending lama, buat order_id baru"""
    user = request.user
    if user.role != 'mentee':
        return Response({'error': 'Akses ditolak'}, status=403)

    booking_id = request.data.get('booking_id')

    try:
        booking = Booking.objects.get(
            id=booking_id, mentee=user, status='completed'
        )
    except Booking.DoesNotExist:
        return Response({'error': 'Booking tidak ditemukan atau sesi belum selesai'}, status=404)

    # Cek kalau sudah success
    if Payment.objects.filter(booking=booking, status='success').exists():
        return Response({'error': 'Tagihan ini sudah dibayar'}, status=400)

    # FIX: HAPUS semua payment pending lama untuk booking ini
    # agar order_id tidak duplikat di Midtrans
    Payment.objects.filter(booking=booking, status='pending').delete()

    amount = int(booking.invoice_amount)
    platform_fee = int(amount * PLATFORM_FEE_PCT)
    mentor_revenue = amount - platform_fee

    # Buat order_id baru yang selalu unik
    order_id = f"EDM-{booking.id}-{uuid.uuid4().hex[:8].upper()}"

    payment = Payment.objects.create(
        booking=booking,
        order_id=order_id,
        amount=amount,
        platform_fee=platform_fee,
        mentor_revenue=mentor_revenue,
        status='pending',
    )

    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": amount,
        },
        "customer_details": {
            "first_name": user.username,
            "email": user.email,
        },
        "item_details": [{
            "id": f"SESSION-{booking.id}",
            "price": amount,
            "quantity": 1,
            "name": f"Sesi Mentoring dengan {booking.mentor_name}",
        }],
    }

    try:
        transaction = snap.create_transaction(param)
        payment.snap_token = transaction['token']
        payment.payment_link = transaction['redirect_url']
        payment.save()

        return Response({
            'token': transaction['token'],
            'redirect_url': transaction['redirect_url'],
            'order_id': order_id,
            'amount': amount,
            'platform_fee': platform_fee,
            'mentor_revenue': mentor_revenue,
        })
    except Exception as e:
        payment.delete()
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_payment_status(request, booking_id):
    """Cek status payment untuk booking tertentu"""
    user = request.user
    try:
        booking = Booking.objects.get(id=booking_id, mentee=user)
        payment = Payment.objects.get(booking=booking)
        return Response({
            'status': payment.status,
            'amount': int(payment.amount),
            'paid_at': payment.paid_at,
            'order_id': payment.order_id,
        })
    except (Booking.DoesNotExist, Payment.DoesNotExist):
        return Response({'status': 'no_payment'})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def midtrans_notification(request):
    """
    Webhook dari Midtrans.
    Untuk development gunakan ngrok:
      ngrok http 8000
    Set di Midtrans sandbox dashboard:
      https://xxxx.ngrok.io/api/payments/webhook/
    """
    data = request.data
    order_id            = data.get('order_id')
    transaction_status  = data.get('transaction_status')
    fraud_status        = data.get('fraud_status', 'accept')
    gross_amount        = data.get('gross_amount')
    midtrans_tx_id      = data.get('transaction_id')
    signature_key       = data.get('signature_key')

    # Verifikasi signature
    raw = f"{order_id}{gross_amount}{settings.MIDTRANS_SERVER_KEY}"
    expected = hashlib.sha512(raw.encode()).hexdigest()
    if signature_key != expected:
        return Response({'error': 'Invalid signature'}, status=403)

    try:
        payment = Payment.objects.get(order_id=order_id)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=404)

    booking = payment.booking

    if transaction_status in ('capture', 'settlement') and fraud_status == 'accept':
        payment.status = 'success'
        payment.paid_at = timezone.now()
        payment.save()

        # Update booking → paid
        booking.status = 'paid'
        booking.save()

        # Update MentoringSession
        try:
            from sessions.models import MentoringSession
            session = MentoringSession.objects.get(booking=booking)
            session.status = 'completed'
            session.save()
        except Exception:
            pass

    elif transaction_status in ('deny', 'cancel', 'expire', 'failure'):
        payment.status = 'failed'
        payment.save()

    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentor_earnings(request):
    """Pendapatan mentor — hanya dari payment success"""
    user = request.user
    if user.role != 'mentor':
        return Response({'error': 'Akses ditolak'}, status=403)

    paid_payments = Payment.objects.filter(
        booking__mentor=user, status='success'
    )
    total_revenue = sum(
        Decimal(str(p.mentor_revenue)) for p in paid_payments
    )

    total_withdrawn = WithdrawalRequest.objects.filter(
        mentor=user, status='approved'
    ).aggregate(total=models.Sum('net_amount'))['total'] or Decimal('0')

    available = total_revenue - total_withdrawn

    unpaid_count = Booking.objects.filter(
        mentor=user, status='completed'
    ).count()

    return Response({
        'total':            int(total_revenue),
        'available_balance':int(available),
        'total_withdrawn':  int(total_withdrawn),
        'unpaid_sessions':  unpaid_count,
        'platform_fee_pct': 10,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_withdrawal(request):
    """Mentor ajukan pencairan saldo"""
    user = request.user
    if user.role != 'mentor':
        return Response({'error': 'Akses ditolak'}, status=403)

    try:
        amount = Decimal(str(request.data.get('amount', 0)))
    except Exception:
        return Response({'error': 'Jumlah tidak valid'}, status=400)

    if amount < Decimal('50000'):
        return Response({'error': 'Minimal pencairan Rp 50.000'}, status=400)

    bank_name      = request.data.get('bank_name', '')
    account_number = request.data.get('account_number', '')
    account_name   = request.data.get('account_name', '')

    # Hitung saldo tersedia
    paid_payments = Payment.objects.filter(booking__mentor=user, status='success')
    total_revenue = sum(Decimal(str(p.mentor_revenue)) for p in paid_payments)
    total_withdrawn = WithdrawalRequest.objects.filter(
        mentor=user, status='approved'
    ).aggregate(total=models.Sum('net_amount'))['total'] or Decimal('0')
    available = total_revenue - total_withdrawn

    if amount > available:
        return Response({
            'error': f'Saldo tidak cukup. Tersedia: Rp {int(available):,}'
        }, status=400)

    withdrawal = WithdrawalRequest.objects.create(
        mentor=user,
        amount=amount,
        gross_amount=amount,
        admin_fee_deducted=Decimal('0'),
        net_amount=amount,
        bank_name=bank_name,
        account_number=account_number,
        account_name=account_name,
        status='pending',
    )

    return Response({
        'message': f'Permintaan pencairan Rp {int(amount):,} berhasil diajukan.',
        'withdrawal_id': withdrawal.id,
        'net_amount': int(amount),
        'note': 'Dana diproses admin dalam 1–3 hari kerja.',
    })


class WithdrawalHistoryView(generics.ListAPIView):
    """Riwayat pencairan mentor — pagination + filter status"""
    serializer_class = WithdrawalHistorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status']
    ordering_fields = ['created_at']

    def get_queryset(self):
        if self.request.user.role != 'mentor':
            return WithdrawalRequest.objects.none()
        return WithdrawalRequest.objects.filter(mentor=self.request.user).order_by('-created_at')

# SESUDAH
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_payment_success(request):
    """Simulasi webhook Midtrans untuk environment tanpa webhook publik — hanya aktif saat DEBUG=True"""
    if not settings.DEBUG:
        return Response({'error': 'Endpoint ini hanya tersedia di mode DEBUG'}, status=403)

    booking_id = request.data.get('booking_id')
    try:
        booking = Booking.objects.get(id=booking_id, mentee=request.user)
        try:
            payment = Payment.objects.get(booking=booking)
        except Payment.DoesNotExist:
            payment = Payment.objects.create(
                booking=booking,
                order_id=f"SIM-{booking.id}",
                amount=booking.invoice_amount,
                platform_fee=int(booking.invoice_amount * Decimal('0.10')),
                mentor_revenue=int(booking.invoice_amount * Decimal('0.90')),
            )
        
        payment.status = 'success'
        payment.paid_at = timezone.now()
        payment.save()
        booking.status = 'paid'
        booking.save()
        
        try:
            from sessions.models import MentoringSession
            session = MentoringSession.objects.get(booking=booking)
            session.status = 'completed'
            session.save()
        except Exception:
            pass
            
        return Response({'message': 'Simulasi berhasil', 'booking_id': booking_id})
    except (Booking.DoesNotExist, Exception) as e:
        return Response({'error': str(e)}, status=404)