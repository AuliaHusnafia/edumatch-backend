from django.urls import path
from . import views

urlpatterns = [
    path('create/',              views.create_review,  name='create-review'),
    path('check/<int:booking_id>/', views.check_review, name='check-review'),
    path('mentor/<int:mentor_id>/', views.mentor_reviews, name='mentor-reviews'),
]