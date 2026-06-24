from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from bookings.models import Booking
from sessions.models import MentoringSession
from .models import Review


@extend_schema(
    summary="Buat review untuk sesi yang sudah selesai dan dibayar",
    tags=["reviews"],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'booking_id': {'type': 'integer', 'description': 'ID booking yang sudah paid'},
                'rating':     {'type': 'integer', 'description': '1-5'},
                'comment':    {'type': 'string',  'description': 'Komentar opsional'},
            },
            'required': ['booking_id', 'rating'],
        }
    },
    examples=[
        OpenApiExample('Contoh', value={'booking_id': 1, 'rating': 5, 'comment': 'Mentor sangat membantu!'})
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request):
    """Mentee membuat review setelah sesi selesai dan lunas."""
    user = request.user
    if user.role != 'mentee':
        return Response({'error': 'Hanya mentee yang bisa memberi review'}, status=403)

    booking_id = request.data.get('booking_id')
    rating     = request.data.get('rating')
    comment    = request.data.get('comment', '')

    # Validasi rating
    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'Rating harus angka 1-5'}, status=400)

    if not booking_id:
        return Response({'error': 'booking_id wajib diisi'}, status=400)

    # Booking harus milik mentee ini dan sudah paid
    try:
        booking = Booking.objects.get(id=booking_id, mentee=user, status='paid')
    except Booking.DoesNotExist:
        return Response({'error': 'Booking tidak ditemukan atau belum lunas'}, status=404)

    # Cek sudah pernah review belum
    # Review terhubung ke MentoringSession — cari session dari booking
    try:
        session = MentoringSession.objects.get(booking=booking)
    except MentoringSession.DoesNotExist:
        # Kalau session tidak ada, tetap bisa review langsung ke mentor
        # dengan menyimpan tanpa session (kita perlu adjust model sedikit)
        # — tapi karena model pakai OneToOne ke session, buat session dulu
        session = MentoringSession.objects.create(
            booking=booking,
            mentee=booking.mentee,
            mentor=booking.mentor,
            mentee_name=booking.mentee_name,
            mentor_name=booking.mentor_name,
            date=booking.date,
            notes=booking.notes,
            status='completed',
        )

    # Cek duplikat review
    if Review.objects.filter(session=session).exists():
        return Response({'error': 'Kamu sudah pernah mereview sesi ini'}, status=400)

    review = Review.objects.create(
        session=session,
        mentee=user,
        mentor=booking.mentor,
        mentee_name=booking.mentee_name,
        mentor_name=booking.mentor_name,
        rating=rating,
        comment=comment,
    )

    return Response({
        'message': 'Review berhasil dikirim!',
        'review_id': review.id,
        'rating': review.rating,
        'comment': review.comment,
    }, status=201)


@extend_schema(
    summary="Cek apakah mentee sudah review booking tertentu",
    tags=["reviews"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_review(request, booking_id):
    """Cek status review untuk booking tertentu."""
    user = request.user
    try:
        booking = Booking.objects.get(id=booking_id, mentee=user)
        session = MentoringSession.objects.get(booking=booking)
        review  = Review.objects.get(session=session)
        return Response({
            'has_review': True,
            'rating':     review.rating,
            'comment':    review.comment,
            'created_at': review.created_at,
        })
    except (Booking.DoesNotExist, MentoringSession.DoesNotExist, Review.DoesNotExist):
        return Response({'has_review': False})


@extend_schema(
    summary="Daftar semua review yang diterima mentor",
    tags=["reviews"],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mentor_reviews(request, mentor_id):
    """Ambil semua review untuk mentor tertentu (publik)."""
    reviews = Review.objects.filter(mentor_id=mentor_id).order_by('-created_at')
    data = [{
        'id':         r.id,
        'mentee_name': r.mentee_name,
        'rating':     r.rating,
        'comment':    r.comment,
        'created_at': r.created_at,
    } for r in reviews]

    avg = sum(r['rating'] for r in data) / len(data) if data else 0
    return Response({
        'mentor_id':    mentor_id,
        'total_reviews': len(data),
        'average_rating': round(avg, 1),
        'reviews':      data,
    })