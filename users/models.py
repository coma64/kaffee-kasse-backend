from django.contrib.auth.models import User
from django.db.models import (
    CASCADE,
    BooleanField,
    DecimalField,
    Model,
    OneToOneField,
    TextField,
)
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


class Profile(Model):
    user = OneToOneField(User, on_delete=CASCADE)
    is_freeloader = BooleanField(default=False)
    balance = DecimalField(max_digits=15, decimal_places=2, default=0)
    bio = TextField(default='')


@receiver(post_save, sender=User)
def create_auth_token(
    sender, instance: User = None, created: bool = False, **kwargs
) -> None:
    if created:
        Token.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_profile(
    sender, instance: User = None, created: bool = False, **kwargs
) -> None:
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance: User, **kwargs) -> None:
    instance.profile.save()
