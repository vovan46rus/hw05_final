import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_author = User.objects.create_user(
            username='post_author',
        )
        cls.non_post_author = User.objects.create_user(
            username='non_post_author',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.post_author,
            image=SimpleUploadedFile(
                name='another_small_default.gif',
                content=SMALL_GIF,
                content_type='image/gif'
            )
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.post_author)
        self.authorized_user_second = Client()
        self.authorized_user_second.force_login(self.non_post_author)

    def test_authorized_user_create_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
            'image': self.image
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.post_author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group_id, form_data['group'])
        self.assertEqual(post.image.name, 'posts/small.gif')

    def test_authorized_user_edit_post(self):
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.post_author,
            group=self.group,
            image=self.image
        )
        uploaded = SimpleUploadedFile(
            name='other_small.gif',
            content=SMALL_GIF,
            content_type='image/gif')
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_user.post(
            reverse(
                'posts:post_edit',
                args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        created_post = Post.objects.get(id=post.id)
        self.assertEqual(created_post.text, form_data['text'])
        self.assertEqual(created_post.author, post.author)
        self.assertEqual(created_post.group_id, form_data['group'])
        self.assertEqual(created_post.pub_date, post.pub_date)
        self.assertEqual(created_post.image.name, 'posts/other_small.gif')

    def test_nonauthorized_user_create_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
        }
        response = self.guest_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse('login') + '?next=' + reverse('posts:post_create')
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_nonauthorized_user_edit_post(self):
        posts_count = Post.objects.count()
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.post_author,
            group=self.group,
        )
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id,
        }
        response = self.guest_user.post(
            reverse(
                'posts:post_edit',
                args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        edited_post = Post.objects.get(id=post.id)
        redirect = reverse('login') + '?next=' + reverse('posts:post_edit',
                                                         kwargs={'post_id':
                                                                 post.id})
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(edited_post.pub_date, post.pub_date)
        self.assertEqual(edited_post.author, post.author)
        self.assertEqual(edited_post.text, post.text)
        self.assertEqual(edited_post.group, post.group)

    def test_authorized_user_not_edit_post(self):
        posts_count = Post.objects.count()
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.post_author,
            group=self.group,
        )
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id,
        }
        response = self.authorized_user_second.post(
            reverse(
                'posts:post_edit',
                args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse('posts:post_detail', kwargs={'post_id': post.id})
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        edited_post = Post.objects.get(id=post.id)
        self.assertEqual(post.text, edited_post.text)
        self.assertEqual(post.author, edited_post.author)
        self.assertEqual(post.group, edited_post.group)
        self.assertEqual(post.pub_date, edited_post.pub_date)

    def test_authorized_user_create_post_without_group(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.post_author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group, None)

    def test_authorized_user_can_add_comment(self):
        comments_count = Comment.objects.count()
        comment = reverse(
            'posts:add_comment',
            kwargs={
                'post_id': self.post.id})
        form_data = {
            'text': 'Тестовый комментарий'
        }
        self.authorized_user.post(
            comment,
            data=form_data,
            follow=True
        )
        new_comment = Comment.objects.last()
        self.assertEqual(comments_count + 1, Comment.objects.count())
        self.assertEqual(new_comment.text, form_data['text'])
        self.assertEqual(new_comment.author, self.post_author)
        self.assertEqual(new_comment.post, self.post)

    def test_nonauthorized_user_can_add_comment(self):
        comments_count = Comment.objects.count()
        comment = reverse(
            'posts:add_comment',
            kwargs={
                'post_id': self.post.id})
        form_data = {
            'text': 'Тестовый комментарий неавторизованного'
        }
        self.guest_user.post(
            comment,
            data=form_data,
            follow=True
        )
        self.assertEqual(comments_count, Comment.objects.count())
