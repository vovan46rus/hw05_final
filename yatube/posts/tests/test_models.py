from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()

STR_NUMBER = 15


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст для поста в котором больше 15 символов.'
        )

    def test_models_have_correct_object_names(self):
        expected_object_name = PostModelTest.post.text[:STR_NUMBER]
        group = PostModelTest.group
        group_title = group.title
        self.assertEqual(group_title, str(group))
        self.assertEqual(expected_object_name, str(PostModelTest.post))
