from typing import List

from django.db.models import Count, F, QuerySet
from django.urls import reverse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from users.models import Profile
from .models import BeverageType, Purchase
from .serializers import (
    BeverageTypeSerializer,
    PurchaseCountSerializer,
    PurchaseSerializer,
)


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
        queryset = super().get_queryset()
        qp = self.request.query_params
        name = qp.get('name', None)

        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class PurchaseViewSet(ModelViewSet):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer

    _orders = ('user', '-user', 'date', '-date', 'beverage_type', '-beverage_type')

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
            Profile.objects.filter(id=self.request.user.id).update(
                balance=F('balance') - beverage_type.price
            )

        return super().perform_create(serializer)

    def get_queryset(self) -> QuerySet:
        """Support `Purchase.user`, `Purchase.beverage_type` and non default order queries"""
        queryset = super().get_queryset()
        qp = self.request.query_params
        user_id, beverage_type_id, order = (
            qp.get('user', None),
            qp.get('beverage_type', None),
            qp.get('order', None),
        )

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
        if order in self._orders:
            queryset = queryset.order_by(order)

        return queryset

    def get_serializer_context(self):
        """Set request to none to return relative urls for relationships"""
        return {'request': None, 'format': self.format_kwarg, 'view': self}

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

    @action(detail=False, methods=['get'])
    def counts(self, request: Request) -> Response:
        """Action for counts of each beverage type"""
        order, user_id = request.query_params.get('order'), request.query_params.get(
            'user'
        )

        if order not in ('count', '-count'):
            order = 'count'

        if user_id is not None:
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None

        purchases = (
            self.get_queryset().filter(user=user_id)
            if user_id is not None
            else self.get_queryset()
        )
        purchase_counts = list(
            purchases.values('beverage_type')
            .annotate(count=Count('beverage_type'))
            .order_by(order)
        )
        for purchase_count in purchase_counts:
            purchase_count['beverage_type'] = reverse(
                'beveragetype-detail', args=[purchase_count['beverage_type']]
            )

        serializer = PurchaseCountSerializer(
            purchase_counts, many=True, context=self.get_serializer_context()
        )

        return Response(serializer.data)
