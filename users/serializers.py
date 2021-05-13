from django.contrib.auth.models import User
from rest_framework.fields import DecimalField
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    ModelSerializer,
    Serializer,
)

from .models import Profile


class UserSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'is_staff', 'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined', 'profile']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 8}}

    def create(self, validate_data):
        """Create a new user with encrypted password and return it"""
        return User.objects.create_user(**validate_data)

    def update(self, instance, validate_data):
        """Set user password correctly"""
        password = validate_data.pop('password', None)
        user = super().update(instance, validate_data)

        if password:
            user.set_password(password)
        user.save()

        return user


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'is_freeloader', 'balance', 'bio']
        read_only_fields = ['id']


class BalanceAddSerializer(Serializer):
    balance = DecimalField(max_digits=15, decimal_places=2)
