from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'university', 'is_verified', 'phone']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="Email sudah terdaftar")]
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'university', 'phone']

    def create(self, validated_data):
        # Jika mentor, set is_verified = False (perlu verifikasi admin)
        role = validated_data.get('role', 'mentee')
        is_verified = False if role == 'mentor' else True
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=role,
            university=validated_data.get('university', ''),
            phone=validated_data.get('phone', ''),
            is_verified=is_verified
        )
        return user