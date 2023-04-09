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

from posts.models import Follow, Group, Post

User = get_user_model()

FIRST_OBJECT: int = 0
NUMBER_OF_POSTS: int = 15
EXPECTED_POSTS_NUMBER: int = 10
EXPECTED_POSTS_NUMBER_ON_SECOND_PAGE: int = 5

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
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
        cls.user = User.objects.create(username='name')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded
        )
        cls.index_url = reverse('posts:index')
        cls.group_list_url = reverse(
            'posts:group_list', kwargs={'slug': cls.group.slug}
        )
        cls.profile_url = reverse(
            'posts:profile', kwargs={'username': cls.post.author}
        )
        cls.post_detail_url = reverse(
            'posts:post_detail', kwargs={'post_id': cls.post.id}
        )
        cls.post_edit_url = reverse(
            'posts:post_edit', kwargs={'post_id': cls.post.id}
        )
        cls.post_create_url = reverse('posts:post_create')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        templates_page_names = {
            self.index_url: 'posts/index.html',
            self.group_list_url: 'posts/group_list.html',
            self.profile_url: 'posts/profile.html',
            self.post_detail_url: 'posts/post_detail.html',
            self.post_edit_url: 'posts/create_post.html',
            self.post_create_url: 'posts/create_post.html',
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def check_post(self, post):
        self.assertEqual(
            post.author, self.user
        )
        self.assertEqual(
            post.text, self.post.text
        )
        self.assertEqual(
            post.group, self.group
        )
        self.assertEqual(
            post.id, self.post.id
        )
        self.assertEqual(
            post.image, self.post.image
        )

    def test_index_show_correct_context(self):
        response = self.client.get(self.index_url)
        post = response.context['page_obj'][FIRST_OBJECT]
        self.check_post(post)

    def test_group_list_show_correct_context(self):
        response = self.client.get(self.group_list_url)
        post = response.context['page_obj'][FIRST_OBJECT]
        self.check_post(post)

    def test_profile_show_correct_context(self):
        response = self.authorized_client.get(
            self.profile_url
        )
        post = response.context['page_obj'][FIRST_OBJECT]
        self.check_post(post)

    def test_post_detail_show_correct_context(self):
        response = self.client.get(self.post_detail_url)
        post = response.context.get('post')
        self.check_post(post)

    def test_create_edit_show_correct_context(self):
        response = self.authorized_client.get(
            self.post_edit_url
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                posts_image = Post.objects.first().image
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
                self.assertEqual(posts_image, 'posts/small.gif')

    def test_create_show_correct_context(self):
        response = self.authorized_client.get(
            self.post_create_url
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field,
                                      expected
                                      )

    def test_check_group_in_index(self):
        form_fields = {
            self.index_url:
            Post.objects.get(group=self.post.group),
            self.group_list_url:
                Post.objects.get(group=self.post.group),
            self.profile_url:
                Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        form_fields = {
            self.group_list_url:
                Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertNotIn(expected, form_field)

    def test_check_cache(self):
        response = self.client.get(reverse('posts:index'))
        first_response = response.content
        Post.objects.first().delete()
        response2 = self.client.get(reverse('posts:index'))
        second_response = response2.content
        self.assertEqual(first_response, second_response)
        cache.clear()
        response3 = self.client.get(reverse('posts:index'))
        third_response = response3.content
        self.assertNotEqual(second_response, third_response)

    def test_home_page_contains_image_in_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        context_image = response.context.get('post').image
        image_expected = Post.objects.get(id=1).image
        self.assertEqual(context_image, image_expected)

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
            'text': 'Тестовый текст',
            'image': uploaded,
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

    def test_404_page_uses_custom_template(self):
        response = self.authorized_client.get('/unexisiting_page/')
        self.assertTemplateUsed(response, 'core/404.html')


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
            description='Тестовое описание'
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


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='user')
        cls.user2 = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            text='Подписаться', author=cls.user2
        )

    def setUp(self):
        self.user1 = FollowTest.user1
        self.user2 = FollowTest.user2
        self.authorized_client1 = Client()
        self.authorized_client1.force_login(self.user1)
        cache.clear()

    def test_follow(self):
        follower = self.user1
        fav_author = self.user2
        self.authorized_client1.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': fav_author.username}
            )
        )
        follower_subscribed_to = Follow.objects.get(user_id=follower.id).author
        self.assertEqual(follower_subscribed_to, fav_author)
        self.authorized_client1.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': fav_author.username}
            )
        )
        follower_subscribed_to = Follow.objects.all()
        self.assertEqual(len(follower_subscribed_to), 0)

    def test_new_author_post_on_follow_index_page(self):
        subscription = Follow.objects.create(
            user=self.user1, author=self.user2
        )
        response = self.authorized_client1.get(reverse('posts:follow_index'))
        new_post = response.context.get('page_obj').object_list[0]
        expected_post = self.post
        self.assertEqual(new_post, expected_post)
        subscription.delete()
        response = self.authorized_client1.get(reverse('posts:follow_index'))
        post_list = response.context.get('page_obj').object_list
        self.assertEqual(len(post_list), 0)
