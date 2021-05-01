from contextlib import contextmanager
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


@contextmanager
def token_auth(test: APITestCase, token: str) -> None:
    old_creds = test.client._credentials

    test.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    yield
    test.client.credentials(**old_creds)


class UsersTest(APITestCase):
    password: str
    user1: User
    user2: User
    staff: User
    user1_token: str
    staff_token: str
    api_uri = '/api/users'

    @classmethod
    def setUpTestData(cls) -> None:
        cls.password = '1234'
        cls.user1 = User.objects.create_user(username='erni', password=cls.password)
        cls.user2 = User.objects.create_user(username='ducky', password=cls.password)
        cls.staff = User.objects.create_superuser(
            username='staff', password=cls.password
        )
        cls.user1_token = Token.objects.get(user=cls.user1).key
        cls.staff_token = Token.objects.get(user=cls.staff).key

    @property
    def user1_uri(self) -> str:
        return f'{self.api_uri}/{self.user1.id}/'

    @property
    def user2_uri(self) -> str:
        return f'{self.api_uri}/{self.user2.id}/'

    def test_me_endpoint(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/me/')

            self.assertEqual(response.data['id'], self.user1.id)

    def test_token_auth(self) -> None:
        response = self.client.post(
            '/api-token-auth/',
            {'username': self.user1.username, 'password': self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

    def test_anyone_can_create(self) -> None:
        response = self.client.post(
            f'{self.api_uri}/', {'username': 'bert', 'password': '1234'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_can_set_profile_fields_on_user_create(self) -> None:
        response = self.client.post(
            f'{self.api_uri}/',
            {'username': 'bert', 'password': '1234', 'profile': {'bio': 'hi there'}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_users_can_list_and_retrieve_all_users(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get(self.user2_uri)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_cant_update_or_delete_other_users(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.put(
                self.user2_uri, {'username': 'otto'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.patch(
                self.user2_uri, {'username': 'otto'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.delete(self.user2_uri)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_can_update_and_delete_themselves(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.put(
                self.user1_uri, {'username': 'otto'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.patch(
                self.user1_uri, {'username': 'bernd'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.delete(self.user1_uri)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            # Restore user
            self.user1.save()

    def test_staff_has_full_access(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.put(
                self.user1_uri, {'username': 'otto'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.patch(
                self.user1_uri, {'username': 'bernd'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.delete(self.user1_uri)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            # Restore user
            self.user1.save()

    def test_is_staff_query(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?is_staff=1')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for user in response.data:
                self.assertTrue(user['is_staff'])

            response = self.client.get(f'{self.api_uri}/?is_staff=0')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for user in response.data:
                self.assertFalse(user['is_staff'])

    def test_is_staff_query_ignores_wrong_type(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?is_staff=has-to-be-0-or-1')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_username_query(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?username=er')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for user in response.data:
                self.assertIn('er', user['username'].lower())


class ProfilesTest(APITestCase):
    password: str
    user1: User
    user2: User
    staff: User
    user1_token: str
    staff_token: str
    api_uri = '/api/profiles'

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

    @property
    def profile1_uri(self) -> str:
        return f'{self.api_uri}/{self.user1.id}/'

    @property
    def profile2_uri(self) -> str:
        return f'{self.api_uri}/{self.user2.id}/'

    def test_no_one_can_create_or_destroy_profiles(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.post(f'{self.api_uri}/')
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

            response = self.client.delete(self.profile1_uri)
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_users_can_update_their_bio(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.put(
                self.profile1_uri, {'bio': 'new bio'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.patch(
                self.profile1_uri, {'bio': 'another bio'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_cant_update_balance(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.put(
                self.profile1_uri, {'balance': '22.22'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.patch(
                self.profile1_uri, {'balance': '22.22'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_cant_update_is_freeloader(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.put(
                self.profile1_uri, {'is_freeloader': True}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            response = self.client.patch(
                self.profile1_uri, {'is_freeloader': True}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_update_balance(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.put(
                self.profile1_uri, {'balance': '22.22'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.patch(
                self.profile1_uri, {'balance': '22.22'}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_can_update_is_freeloader(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.put(
                self.profile1_uri, {'is_freeloader': True}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.patch(
                self.profile1_uri, {'is_freeloader': True}, format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_cant_access_add_balance(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.patch(
                f'{self.api_uri}/{self.user1.id}/add-balance/',
                {'balance': '12.34'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_access_add_balance(self) -> None:
        with token_auth(self, self.staff_token):
            response = self.client.patch(
                f'{self.api_uri}/{self.user1.id}/add-balance/',
                {'balance': '12.34'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_balance(self) -> None:
        with token_auth(self, self.staff_token):
            self.user1.refresh_from_db()
            previous_balance = self.user1.profile.balance

            response = self.client.patch(
                f'{self.api_uri}/{self.user1.id}/add-balance/',
                {'balance': '12.34'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.user1.refresh_from_db()
            new_balance = self.user1.profile.balance
            self.assertEqual(new_balance, previous_balance + Decimal('12.34'))

    def test_is_freeloader_query(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?is_freeloader=1')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for user in response.data:
                self.assertTrue(user['is_freeloader'])

            response = self.client.get(f'{self.api_uri}/?is_freeloader=0')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for user in response.data:
                self.assertFalse(user['is_freeloader'])

    def test_is_freeloader_query_ignores_wrong_type(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(
                f'{self.api_uri}/?is_freeloader=has-to-be-0-or-1'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bio_query(self) -> None:
        with token_auth(self, self.user1_token):
            response = self.client.get(f'{self.api_uri}/?bio=hi')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            for user in response.data:
                self.assertIn('hi', user['bio'].lower())
