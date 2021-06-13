from rest_framework.fields import IntegerField
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    ModelSerializer,
    Serializer,
    URLField,
)

from .models import BeverageType, Purchase


class BeverageTypeSerializer(ModelSerializer):
    class Meta:
        model = BeverageType
        fields = ['id', 'name', 'price']
        read_only_fields = ['id']


class PurchaseSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Purchase
        fields = ['id', 'user', 'beverage_type', 'date']
        read_only_fields = ['id', 'date']


class PurchaseCountSerializer(Serializer):
    class Meta:
        read_only_fields = ['beverage_type', 'count']

    beverage_type = URLField()
    count = IntegerField()
