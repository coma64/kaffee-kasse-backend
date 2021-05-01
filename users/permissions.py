from django.contrib.auth.models import User
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import Profile


class IsUserOwnerOrStaff(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request: Request, view, user: User) -> bool:
        return user.pk == request.user.pk or request.user.is_staff


class IsProfileOwnerOrStaff(BasePermission):
    staff_only_fields = ('is_freeloader', 'balance')

    def has_permission(self, request: Request, view) -> bool:
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request: Request, view, profile: Profile) -> bool:
        if request.user.is_staff:
            return True
        return profile.pk == request.user.profile.pk and not any(
            [field in request.data for field in IsProfileOwnerOrStaff.staff_only_fields]
        )
