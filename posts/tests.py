import io
import tempfile
from urllib.parse import urljoin

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Comment, Follow, Group, Post, User


class Hw05_Final_Test(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="MegaDen",
            email="di-nis@ya.ru",
        )

        self.auth_client = Client()
        self.auth_client.force_login(self.user)
        self.nonauth_client = Client()
        self.group = Group.objects.create(
            title='RadioFM',
            slug='radiofm',
            description='Только новая музыка'
        )

        self.urls = {
            'index': reverse('index'),
            'post': reverse('post', kwargs={'username': self.user.username,
                                            'post_id': 1}),
            'group_posts': reverse('group_posts',
                                   kwargs={'slug': self.group.slug}),
            'profile': reverse('profile',
                               kwargs={'username': self.user.username})}

    def requests_and_checks(self, url, group, user, text):
        cache.clear()
        response = self.auth_client.get(url)
        if 'paginator' in response.context:
            current_post = response.context['paginator'].object_list.first()
        else:
            current_post = response.context['post_profile']

        self.assertEqual(current_post.text, text)
        self.assertEqual(current_post.group, group)
        self.assertEqual(current_post.author, user)

    def test_profile_available(self):
        response_profile = self.auth_client.get(self.urls['profile'])
        self.assertEqual(response_profile.status_code, 200)

    def test_auth_user_can_publish_new_post(self):
        response_new_post = self.auth_client.post(
            reverse('new_post'),
            data={"text": "Новый текст",
                  "author": self.user,
                  "group": self.group.id},
            follow=True)
        post_counter = Post.objects.count()
        new_post = Post.objects.first()
        self.assertEqual(response_new_post.status_code, 200)
        self.assertEqual(new_post.author,
                         self.user)
        self.assertEqual(new_post.group, self.group)
        self.assertEqual(new_post.text, "Новый текст")
        self.assertEqual(post_counter, 1)

    def test_nonauth_user_cant_publish_new_post(self):
        response_new_post = self.nonauth_client.post(
            reverse('new_post'),
            data={"text": "Новый текст",
                  "author": self.user,
                  "group": self.group.id},
            follow=True)
        post_counter = Post.objects.count()
        url_redirect = urljoin(reverse('login'), '?next='+reverse('new_post'))
        self.assertRedirects(response_new_post, url_redirect)
        self.assertEqual(post_counter, 0)

    def test_new_post_appears_on_pages(self):
        new_post = Post.objects.create(text="Текст нового поста",
                                       author=self.user,
                                       group=self.group)

        for url in self.urls.values():
            self.requests_and_checks(url, new_post.group,
                                     new_post.author, new_post.text)

    def test_auth_user_can_edit_post_and_post_edited_on_pages(self):
        new_group = Group.objects.create(title='Musictv',
                                         slug='musictv',
                                         description='Музыкальный канал')
        post = Post.objects.create(text="Текст нового поста",
                                   author=self.user,
                                   group=self.group)
        response_edit_post = self.auth_client.post(
            reverse('post_edit', kwargs={
                    'username': self.user,
                    'post_id': post.id}),
            data={"text": "Текст измененного поста",
                  "author": self.user,
                  "group": new_group.id},
            follow=True
        )
        post.refresh_from_db()

        for url in self.urls.values():
            self.requests_and_checks(url, new_group,
                                     self.user, post.text)

        response_old_post = self.auth_client.get(self.urls['group_posts'])
        post_counter = response_old_post.context['group'].group_posts.count()

        self.assertNotContains(response_old_post, 'Текст нового поста')
        self.assertEqual(post_counter, 0)

    def test_page_not_found(self):
        response = self.nonauth_client.get('/group/tennis/')
        self.assertEqual(response.status_code, 404)

    def test_find_image_tag_and_post_on_pages(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                byte_image = io.BytesIO()
                im = Image.new("RGB", size=(1000, 1000), color=(255, 0, 0, 0))
                im.save(byte_image, format='jpeg')
                byte_image.seek(0)
                image = ContentFile(byte_image.read(), name='test.jpeg')

        response_new_post = self.auth_client.post(
            reverse('new_post'),
            data={"text": "Новый текст",
                  "author": self.user,
                  "group": self.group.id,
                  "image": image},
            follow=True)
        post_counter = Post.objects.count()

        for url in self.urls:
            response = self.auth_client.get(self.urls[url])

        self.assertContains(response, 'unique_id')
        self.assertContains(response, '<img')
        self.assertEqual(post_counter, 1)

    def test_block_create_post_with_not_image(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                byte_image = io.BytesIO()
                im = Image.new("RGB", size=(1000, 1000), color=(255, 0, 0, 0))
                im.save(byte_image, format='jpeg')
                byte_image.seek(0)
                image = ContentFile(byte_image.read(), name='test.txt')

        response_post = self.auth_client.post(
            reverse('new_post'),
            data={"text": "Новый текст",
                  "author": self.user,
                  "group": self.group.id,
                  "image": image},
            follow=True)
        post_counter = Post.objects.count()

        self.assertEqual(response_post.status_code, 200)
        self.assertEqual(post_counter, 0)

    def test_cache(self):
        post_one = self.auth_client.post(
                reverse('new_post'),
                data={"text": "Текст первого поста",
                      "author": self.user,
                      "group": self.group.id},
                follow=True)
        response_first_post = self.auth_client.get(reverse('index'))

        self.assertNotContains(response_first_post, "Текст первого поста")
        self.assertEqual(post_one.status_code, 200)

        cache.clear()

        post_two = self.auth_client.post(
                reverse('new_post'),
                data={"text": "Текст второго поста",
                      "author": self.user,
                      "group": self.group.id},
                follow=True)

        response_second_post = self.auth_client.get(self.urls['index'])

        self.assertEqual(post_two.status_code, 200)
        self.assertContains(response_second_post, "Текст второго поста")

    def test_auth_user_can_follow(self):
        user_follower = User.objects.create_user(
            username="Fedun",
            email="fedun@ya.ru"
        )
        response_follow = self.auth_client.post(
            reverse('profile_follow', kwargs={
                    'username': user_follower}),
            data={"user": self.user,
                  "author": user_follower},
            follow=True)
        follow_counter = Follow.objects.count()

        self.assertEqual(response_follow.status_code, 200)
        self.assertTrue(response_follow.context['following'])
        self.assertEqual(follow_counter, 1)

    def test_auth_user_can_unfollow(self):
        user_follower = User.objects.create_user(
            username="Fedun",
            email="fedun@ya.ru"
        )

        subscription = Follow.objects.create(
            user=self.user,
            author=user_follower
        )

        response_unfollow = self.auth_client.post(
            reverse('profile_unfollow', kwargs={
                    'username': user_follower}),
            data={"user": self.user,
                  "author": user_follower},
            follow=True)

        follow_counter = Follow.objects.count()
        self.assertEqual(response_unfollow.status_code, 200)
        self.assertFalse(response_unfollow.context['following'])
        self.assertEqual(follow_counter, 0)

    def test_new_post_appears_on_user_follower_pages(self):
        user_follower = User.objects.create_user(
            username="Fedun",
            email="fedun@ya.ru"
        )

        subscription = Follow.objects.create(
            user=self.user,
            author=user_follower
        )

        new_post = Post.objects.create(text="Текст нового поста",
                                       author=user_follower,
                                       group=self.group)

        response_post = self.auth_client.post(reverse('follow_index'))
        post_fol = response_post.context['paginator'].object_list.first()

        self.assertEqual(post_fol.text, "Текст нового поста")

    def test_new_post_not_appears_on_user_nonfollower_pages(self):
        user_nonfollower = User.objects.create_user(
            username="Fedun",
            email="fedun@ya.ru"
        )

        new_post = Post.objects.create(text="Текст нового поста",
                                       author=user_nonfollower,
                                       group=self.group)

        response_post = self.auth_client.post(reverse('follow_index'))
        post_unfol = response_post.context['paginator'].object_list.first()

        post_counter = Post.objects.count()

        self.assertEqual(post_unfol, None)
        self.assertEqual(post_counter, 1)

    def test_auth_user_can_comments(self):
        new_post = Post.objects.create(text="Текст нового поста",
                                       author=self.user,
                                       group=self.group)

        response_comment_auth = self.auth_client.post(
            reverse('add_comment', kwargs={
                    'username': self.user.username,
                    'post_id': new_post.id}),
            data={"post": new_post.id,
                  "author": self.user,
                  "text": "Новый коммент авторизованного пользователя"},
            follow=True)

        comment_counter = Comment.objects.count()
        self.assertEqual(response_comment_auth.status_code, 200)
        self.assertEqual(comment_counter, 1)

    def test_nonauth_user_cant_comments(self):
        new_post = Post.objects.create(text="Текст нового поста",
                                       author=self.user,
                                       group=self.group)

        response_comment_nonauth = self.nonauth_client.post(
            reverse('add_comment', kwargs={
                    'username': self.user.username,
                    'post_id': new_post.id}),
            data={"post": new_post.id,
                  "author": self.user,
                  "text": "Новый коммент авторизованного пользователя"},
            follow=True)

        comment_counter = Comment.objects.count()

        self.assertEqual(comment_counter, 0)

    def tearDown(self):
        print("Тест выполнен")
