from django.contrib.auth.models import User
from django.db.models import (
    CASCADE,
    CharField,
    DateTimeField,
    DecimalField,
    ForeignKey,
    Model,
)


class BeverageType(Model):
    name = CharField(max_length=150)
    price = DecimalField(max_digits=15, decimal_places=2)


class Purchase(Model):
    beverage_type = ForeignKey(BeverageType, CASCADE)
    user = ForeignKey(User, CASCADE)
    date = DateTimeField(auto_now_add=True)
