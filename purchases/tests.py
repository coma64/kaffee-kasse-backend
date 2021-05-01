from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from users.tests import token_auth

from .models import BeverageType, Purchase


class PurchasesTest(APITestCase):
    api_uri = '/api/purchases'
    beverage_type_api_uri = '/api/beverage-types'
    user_api_uri = '/api/users'
    password: str
    user1: User
    user2: User
    staff: User
    user1_token: str
    staff_token: str
    purchase1: Purchase
    purchase2: Purchase
    beverage_type: BeverageType

    @classmethod
    def setUpTestData(cls) -> None:
        cls.password = '1234'
        cls.user1 = User.objects.create_user(username='erni', password=cls.password)
        cls.user1.profile.bio = 'hi there'
        cls.user2 = User.objects.create_user(username='ducky', password=cls.password)
        cls.user2.profile.bio = 'hello'
        cls.staff = User.objects.create_superuser(
            username='staff', password=cls.password
        )
        cls.user1_token = Token.objects.get(user=cls.user1).key
        cls.staff_token = Token.objects.get(user=cls.staff).key
        cls.beverage_type = BeverageType.objects.create(name='coffee', price=2.22)
        # Without refreshing the type will be float
        cls.beverage_type.refresh_from_db()
        cls.purchase1 = Purchase.objects.create(
            beverage_type=cls.beverage_type, user=cls.user1
        )
        cls.purchase2 = Purchase.objects.create(
            beverage_type=cls.beverage_type, user=cls.user2
        )

    @property
    def purchase1_uri(self) -> str:
        return f'{self.api_uri}/{self.purchase2.id}/'

    @property
    def purchase2_uri(self) -> str:
        return f'{self.api_uri}/{self.purchase2.id}/'

    @property
    def beverage_type_uri(self) -> str:
        return f'{self.beverage_type_api_uri}/{self.beverage_type.id}/'

    @property
    def user1_uri(self) -> str:
        return f'{self.user_api_uri}/{self.user1.id}/'

    @property
    def user2_uri(self) -> str:
        return f'{self.user_api_uri}/{self.user2.id}/'

    def test_users_can_create_purchases_for_themselves(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.post(
                f'{self.api_uri}/',
                {'beverage_type': self.beverage_type_uri, 'user': self.user1_uri},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_users_cant_create_purchases_for_others(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.post(
                f'{self.api_uri}/',
                {'beverage_type': self.beverage_type_uri, 'user': self.user2_uri},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create_purchases_for_others(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.post(
                f'{self.api_uri}/',
                {'beverage_type': self.beverage_type_uri, 'user': self.user2_uri},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_users_can_list_and_retrieve_purchases(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get(self.purchase1_uri)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_cant_delete_or_update_purchases(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.put(
                self.purchase1_uri,
                {'beverage_type': self.beverage_type_uri},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.patch(
                self.purchase1_uri,
                {'beverage_type': self.beverage_type_uri},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.delete(self.purchase1_uri)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admins_can_delete_and_update_purchases(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.put(
                self.purchase1_uri,
                {'beverage_type': self.beverage_type_uri, 'user': self.user1_uri},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.patch(
                self.purchase1_uri,
                {'beverage_type': self.beverage_type_uri},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.delete(self.purchase1_uri)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            # Restore purchase
            self.purchase1.save()

    def test_purchase_creation_updates_profile_balance(self) -> None:
        with token_auth(self, self.user1_token):
            self.user1.refresh_from_db()
            previous_balance = self.user1.profile.balance

            response = self.client.post(
                f'{self.api_uri}/',
                {'beverage_type': self.beverage_type_uri, 'user': self.user1_uri},
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            self.user1.refresh_from_db()
            new_balance = self.user1.profile.balance
            self.assertEqual(new_balance, previous_balance - self.beverage_type.price)

    def test_user_query(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?user=1')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for purchase in response.data:
                self.assertIn(self.user1_uri, purchase['user'])

    def test_user_query_ignores_wrong_type(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?user=has-to-be-0-or-1')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_beverage_type_query(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?beverage_type=1')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for purchase in response.data:
                self.assertIn(self.beverage_type_uri, purchase['beverage_type'])

    def test_beverage_type_query_ignores_wrong_type(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(
                f'{self.api_uri}/?beverage_type=has-to-be-0-or-1'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class BeverageTypesTest(APITestCase):
    api_uri = '/api/beverage-types'
    password = '1234'
    user1: User
    user2: User
    staff: User
    user1_token: str
    staff_token: str
    beverage_type1: BeverageType

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user1 = User.objects.create_user(username='erni', password=cls.password)
        cls.user2 = User.objects.create_user(username='ducky', password=cls.password)
        cls.staff = User.objects.create_superuser(
            username='staff', password=cls.password
        )
        cls.user1_token = Token.objects.get(user=cls.user1).key
        cls.staff_token = Token.objects.get(user=cls.staff).key
        cls.beverage_type1 = BeverageType.objects.create(name='coffee', price='2.20')
        cls.beverage_type2 = BeverageType.objects.create(
            name='latte macchiato', price='2.40'
        )

    @property
    def beverage_type_uri(self) -> str:
        return f'{self.api_uri}/{self.beverage_type1.id}/'

    def test_users_can_list_and_retrieve(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get(self.beverage_type_uri)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_cant_create_delete_or_update(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.post(
                f'{self.api_uri}/', {'name': 'beer', 'price': '3.20'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.put(
                self.beverage_type_uri,
                {'name': 'espresso', 'price': '3.20'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.patch(
                self.beverage_type_uri, {'price': '3.30'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.delete(self.beverage_type_uri)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create_delete_and_update(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.post(
                f'{self.api_uri}/', {'name': 'beer', 'price': '3.20'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            response = self.client.put(
                self.beverage_type_uri,
                {'name': 'espresso', 'price': '3.20'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.patch(
                self.beverage_type_uri, {'price': '3.30'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.delete(self.beverage_type_uri)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            # Restore beverage type
            self.beverage_type1.save()

    def test_name_query(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?name=coff')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for user in response.data:
                self.assertIn('coff', user['name'].lower())
