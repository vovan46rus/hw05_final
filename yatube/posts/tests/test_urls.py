from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='post_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание группы'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост'
        )

    def setUp(self):
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(
            User.objects.create_user(username='User2')
        )
        self.guest_client = Client()

    def test_urls_uses_correct_template(self):
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/profile.html': f'/profile/{self.user.username}/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
            'posts/create_post.html': f'/posts/{self.post.id}/edit/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client_author.get(address)
                self.assertTemplateUsed(response, template)

    def test_unauthorized_user_create_redirect(self):
        response = self.guest_client.get(
            '/create/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response,
            '/auth/login/?next=/create/'
        )

    def test_unauthorized_user_edit_redirect(self):
        response = self.guest_client.get(
            f'/posts/{self.post.id}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.id}/edit/'
        )

    def test_unexisting_page_returns_404(self):
        unexisting_page = '/posts/'
        response = self.guest_client.get(unexisting_page)
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND
        )

    def test_redirect_for_not_author_if_try_to_edit_post(self):
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/'
        )
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND
        )
        self.assertRedirects(
            response,
            f'/posts/{self.post.id}/'
        )

    def test_custom_404_template(self):
        unexisting_page = '/posts/'
        response = self.guest_client.get(unexisting_page)
        self.assertTemplateUsed(
            response,
            'core/404.html'
        )
