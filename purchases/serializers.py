from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer

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
