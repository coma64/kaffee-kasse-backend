from typing import List, Type

from django.contrib.auth.models import User
from django.db.models import Count, QuerySet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .models import Profile
from .permissions import IsProfileOwnerOrStaff, IsUserOwnerOrStaff
from .serializers import BalanceAddSerializer, ProfileSerializer, UserSerializer


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    _default_orders = ('username', '-username', 'date_joined', '-date_joined')
    _custom_orders = ('purchases', '-purchases')

    def get_permissions(self) -> List[BasePermission]:
        """Allow creation to anyone, updating, partially updating and
        destroying only to staff and the current user
        """
        permission_classes = [IsAuthenticated]
        if self.action == 'create':
            permission_classes = []
        elif self.action in ('update', 'partial_update', 'destroy'):
            permission_classes += [IsUserOwnerOrStaff]
        return [permission() for permission in permission_classes]

    def get_queryset(self) -> QuerySet:
        """Support `User.is_staff`, `User.username` and non default order queries"""
        queryset = super().get_queryset()
        qp = self.request.query_params
        is_staff, username, order = (
            qp.get('is_staff', None),
            qp.get('username'),
            qp.get('order'),
        )

        if is_staff is not None:
            try:
                is_staff = bool(int(is_staff))
                queryset = queryset.filter(is_staff=is_staff)
            except ValueError:
                pass
        if username is not None:
            queryset = queryset.filter(username__icontains=username)
        if order in self._default_orders:
            queryset = queryset.order_by(order)
        if order in self._custom_orders:
            if order == 'purchases':
                queryset = queryset.annotate(purchases=Count('purchase')).order_by(
                    'purchases', 'pk'
                )
            elif order == '-purchases':
                queryset = queryset.annotate(purchases=Count('purchase')).order_by(
                    '-purchases', 'pk'
                )
        return queryset

    def get_serializer_context(self):
        """Set request to none to return relative urls for relationships"""
        return {'request': None, 'format': self.format_kwarg, 'view': self}

    def create(self, request: Request) -> Response:
        """Allow setting `Profile` fields on `User` creation"""
        user_serializer = self.get_serializer(data=request.data)
        user_serializer.is_valid(raise_exception=True)
        user: User = user_serializer.save()

        if 'profile' in request.data:
            profile_serializer = ProfileSerializer(
                user.profile, data=request.data['profile'], partial=True
            )
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save()

        serializer = self.get_serializer(user)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=False)
    def me(self, request: Request) -> Response:
        """Current user endpoint"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


# Not inheriting CreateModelMixin and DeleteModelMixin to disallow creation
# and deletion, profiles should be created and deleted only through users
class ProfileViewSet(
    RetrieveModelMixin, UpdateModelMixin, ListModelMixin, GenericViewSet
):
    queryset = Profile.objects.all()

    def get_permissions(self) -> List[BasePermission]:
        """Allow `add_balance` only to staff, updating to staff and the current
        user
        """
        permission_classes = [IsAuthenticated]
        if self.action in ('add_balance',):
            permission_classes += [IsAdminUser]
        elif self.action in ('update', 'partial_update'):
            permission_classes += [IsProfileOwnerOrStaff]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self) -> Type[BaseSerializer]:
        """Change serializer class for custom actions"""
        if self.action == 'add_balance':
            return BalanceAddSerializer
        else:
            return ProfileSerializer

    def get_queryset(self) -> QuerySet:
        """Support `Profile.is_freeloader` and `Profile.bio` queries"""
        queryset = super().get_queryset()
        qp = self.request.query_params
        is_freeloader, bio = qp.get('is_freeloader', None), qp.get('bio')

        if is_freeloader is not None:
            try:
                is_freeloader = bool(int(is_freeloader))
                queryset = queryset.filter(is_freeloader=is_freeloader)
            except ValueError:
                pass
        if bio is not None:
            queryset = queryset.filter(bio__icontains=bio)
        return queryset

    @action(detail=True, methods=['patch'], url_path='add-balance')
    def add_balance(self, request: Request, pk: str = None):
        """Helper action for adding to `Profile.balance`"""
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = self.get_object()
        profile.balance += serializer.validated_data['balance']
        profile.save()

        return Response(ProfileSerializer(profile).data)
