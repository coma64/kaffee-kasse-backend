from typing import List

from django.db.models import QuerySet
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import BeverageType, Purchase
from .serializers import BeverageTypeSerializer, PurchaseSerializer


class BeverageTypeViewSet(ModelViewSet):
    queryset = BeverageType.objects.all()
    serializer_class = BeverageTypeSerializer

    def get_permissions(self) -> List[BasePermission]:
        """Allow viewing to authenticated users, creating, deletion and updating only to
        staff
        """
        permission_classes = [IsAuthenticated]
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            permission_classes += [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self) -> QuerySet:
        """Support `BeverageType.name` queries"""
        queryset = self.queryset
        qp = self.request.query_params
        name = qp.get('name', None)

        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class PurchaseViewSet(ModelViewSet):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer

    def get_permissions(self) -> List[BasePermission]:
        """Allow viewing and creating to authenticated users, deletion and
        updating only to staff
        """
        permission_classes = [IsAuthenticated]
        if self.action in ('update', 'partial_update', 'destroy'):
            permission_classes += [IsAdminUser]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer: PurchaseSerializer) -> None:
        """Update `Profile.balance` corresponding to `Purchase.price`"""
        user, beverage_type = (
            serializer.validated_data['user'],
            serializer.validated_data['beverage_type'],
        )
        if not user.profile.is_freeloader:
            user.profile.balance -= beverage_type.price

        user.save()
        return super().perform_create(serializer)

    def get_queryset(self) -> QuerySet:
        """Support `Purchase.user` and `Purchase.beverage_type` queries"""
        queryset = self.queryset
        qp = self.request.query_params
        user_id, beverage_type_id = qp.get('user', None), qp.get('beverage_type', None)

        if user_id is not None:
            try:
                user_id = int(user_id)
                queryset = queryset.filter(user=user_id)
            except ValueError:
                pass
        if beverage_type_id is not None:
            try:
                beverage_type_id = int(beverage_type_id)
                queryset = queryset.filter(beverage_type=beverage_type_id)
            except ValueError:
                pass
        return queryset

    def create(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if (
            serializer.validated_data['user'].id != request.user.id
            and not request.user.is_staff
        ):
            return Response(
                {
                    'user': 'Cannot set user different from authenticated user'
                    'unless staff'
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
