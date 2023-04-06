from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Group, Post

User = get_user_model()


class PostFormTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='name')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test-group',
                                          description='Описание'
                                          )
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )

    def check_forms(self, post, form_data):
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.pk, form_data['group'])

    def test_create_post(self):
        posts_count = Post.objects.count()
        post_content = {
            'text': 'Текст записанный в форму',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=post_content, follow=True
        )

        post = Post.objects.last()
        self.check_forms(post, post_content)
        self.assertEqual(response.status_code,
                         HTTPStatus.OK
                         )
        self.assertEqual(Post.objects.count(),
                         posts_count + 1
                         )

    def test_post_edit(self):
        created_post = Post.objects.create(
            text='Оригинальный текст',
            author=self.user,
            group=self.group
        )
        post_edited_form = {
            'text': 'Редактируем текст',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': created_post.id}),
            data=post_edited_form
        )
        edited_post = Post.objects.get(
            id=created_post.id
        )
        self.check_forms(
            edited_post, post_edited_form)
        self.assertEqual(
            response.status_code, HTTPStatus.FOUND
        )

    def test_authorized_edit_post(self):
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'image': self.uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        post_edit = Post.objects.get(pk=self.group.pk)
        self.client.get(f'/posts/{post_edit.pk}/edit/')
        form_data = {
            'text': 'Измененный пост',
            'group': self.group.pk
        }
        response_edit = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={
                        'post_id': post_edit.pk
                    }),
            data=form_data,
            follow=True,
        )
        post_edit = Post.objects.get(pk=self.group.pk)
        self.assertEqual(
            response_edit.status_code, HTTPStatus.OK
        )
        self.check_forms(
            post_edit, form_data
        )
