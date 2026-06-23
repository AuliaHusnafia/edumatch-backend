from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Booking


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentee_my_bookings(request):
    """Semua booking milik mentee"""
    user = request.user
    bookings = Booking.objects.filter(mentee=user).order_by('-created_at')

    result = []
    for b in bookings:
        result.append({
            'id': b.id,
            'mentor_name': b.mentor_name,
            'date': b.date,
            'notes': b.notes,
            'status': b.status,
            'status_display': b.get_status_display(),
            'meeting_link': b.meeting_link,
            'invoice_amount': float(b.invoice_amount),
            'created_at': b.created_at,
        })
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentee_ongoing_sessions(request):
    """Sesi yang sedang berjalan (accepted / ongoing) — termasuk meeting link"""
    user = request.user
    bookings = Booking.objects.filter(
        mentee=user,
        status__in=['accepted', 'ongoing']
    ).order_by('date')

    result = []
    for b in bookings:
        result.append({
            'id': b.id,
            'mentor_name': b.mentor_name,
            'date': b.date,
            'status': b.status,
            'status_display': b.get_status_display(),
            'meeting_link': b.meeting_link,
            'notes': b.notes,
        })
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentee_completed_sessions(request):
    """Sesi selesai — sekaligus sebagai riwayat + tagihan"""
    user = request.user
    bookings = Booking.objects.filter(
        mentee=user,
        status='completed'
    ).order_by('-updated_at')

    result = []
    for b in bookings:
        result.append({
            'id': b.id,
            'mentor_name': b.mentor_name,
            'date': b.date,
            'status': b.status,
            'notes': b.notes,
            'invoice_amount': float(b.invoice_amount),  # tagihan dari mentor
            'meeting_link': b.meeting_link,
        })
    return Response(result)