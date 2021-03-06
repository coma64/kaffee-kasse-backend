from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from purchases.views import BeverageTypeViewSet, PurchaseViewSet
from users.views import ProfileViewSet, UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('profiles', ProfileViewSet)
router.register(
    'beverage-types',
    BeverageTypeViewSet,
)
router.register('purchases', PurchaseViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-token-auth/', obtain_auth_token),
]
