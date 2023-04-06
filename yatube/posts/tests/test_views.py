import shutil
import tempfile
from typing import List

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()
NUMBER_OF_POSTS: int = 15
EXPECTED_POSTS_NUMBER: int = 10
EXPECTED_POSTS_NUMBER_ON_SECOND_PAGE: int = 5

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostContextTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=uploaded
        )
        

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_index_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index')) 
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_group_list_correct_context(self):
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_post_detail_correct_context(self):
        response = self.client.get(reverse('posts:post_detail',
                                           kwargs={'post_id': self.post.id}))
        first_object = response.context['post']
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_post_create_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={"post_id": f'{self.post.id}'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'author'}))
        first_object = response.context['page_obj'][0]
        posts_text = first_object.text
        posts_image = Post.objects.first().image
        self.assertEqual(posts_image, 'posts/small.gif')
        self.assertEqual(response.context['author'].username, 'author')
        self.assertEqual(posts_text, 'Тестовый пост')

    def test_posts_sorted_by_user(self):
        response = self.client.get(
            reverse('posts:profile',
                    kwargs={'username': self.post.author})
        )
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')

    def test_post_edit_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={"post_id": f'{self.post.id}'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context['is_edit'])

    def test_extended_post_checking(self):
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': 'test_slug'})
        )
        first_object = response.context["page_obj"][0]
        post_1 = first_object.text
        self.assertTrue(post_1, 'Тестовая запись 2')

    def test_creation_post_with_image(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'title': 'Тестовый заголовок',
            'text': 'Тестовый текст',
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(Post.objects.last().image, 'posts/small.gif')
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.user.username})
        )

    def test_check_cache(self):
        response = self.client.get(reverse("posts:index"))
        first_response = response.content
        Post.objects.first().delete()
        response2 = self.client.get(reverse("posts:index"))
        second_response = response2.content
        self.assertEqual(first_response, second_response)
        cache.clear()
        response3 = self.client.get(reverse("posts:index"))
        third_response = response3.content
        self.assertNotEqual(second_response, third_response)


class PaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        list_of_posts: List[Post] = []

        cls.guest_client = Client()

        cls.user = User.objects.create(username='HasNoName')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='some-slug',
            description='Тестовое описание',
        )

        for _ in range(NUMBER_OF_POSTS):
            list_of_posts.append(
                Post(
                    text='Один из многих',
                    author=cls.user,
                    group=cls.group,
                )
            )

        Post.objects.bulk_create(list_of_posts)

    def setUp(self) -> None:
        cache.clear()

    def test_paginator_on_three_pages(self):
        group_page = f'/group/{self.group.slug}/'
        profile_page = f'/profile/{self.user}/'
        main_page = '/'
        second_page = '?page=2'
        pag_main = main_page + second_page
        pag_prof = profile_page + second_page
        pag_group = group_page + second_page

        page_expected_posts = {
            group_page: EXPECTED_POSTS_NUMBER,
            profile_page: EXPECTED_POSTS_NUMBER,
            main_page: EXPECTED_POSTS_NUMBER,
            pag_group: EXPECTED_POSTS_NUMBER_ON_SECOND_PAGE,
            pag_prof: EXPECTED_POSTS_NUMBER_ON_SECOND_PAGE,
            pag_main: EXPECTED_POSTS_NUMBER_ON_SECOND_PAGE,
        }

        for address, expected_number_of_posts in page_expected_posts.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                total_posts_on_page = len(response.context['page_obj'])

                self.assertEqual(
                    total_posts_on_page,
                    expected_number_of_posts
                )
