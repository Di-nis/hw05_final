from urllib.parse import urljoin

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

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

    def test_create_new_post_auth_user(self):
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

    def test_create_new_post_nonauth_user(self):
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

    def test_new_post_on_pages(self):
        cache.clear()
        new_post = Post.objects.create(text="Текст нового поста",
                                       author=self.user,
                                       group=self.group)

        for url in self.urls.values():
            self.requests_and_checks(url, new_post.group,
                                     new_post.author, new_post.text)

    def test_edit_post_auth_user(self):
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

    def test_tag_image_and_image_on_pages(self):
        with open('media/lake.jpg', 'rb') as img:
            response_new_post = self.auth_client.post(
                reverse('new_post'),
                data={"text": "Новый текст",
                      "author": self.user,
                      "group": self.group.id,
                      "image": img},
                follow=True)

        post_counter = Post.objects.count()

        self.assertEqual(response_new_post.status_code, 200)

        for url in self.urls:
            response = self.auth_client.get(self.urls[url])

        self.assertContains(response, 'unique_id')
        self.assertContains(response, '<img')
        self.assertEqual(post_counter, 1)

    def test_post_without_image(self):
        with open('media/test.txt', 'rb') as img:
            response_post = self.auth_client.post(
                reverse('new_post'),
                data={"text": "Новый текст",
                      "author": self.user,
                      "group": self.group.id,
                      "image": img},
                follow=True)

        post_counter = Post.objects.count()

        self.assertEqual(response_post.status_code, 200)
        self.assertEqual(post_counter, 0)

    def test_cache(self):
        post_one = self.auth_client.post(
                reverse('new_post'),
                data={"text": "Пост первого поста",
                      "author": self.user,
                      "group": self.group.id},
                follow=True)
        response_first_post = self.auth_client.get(reverse('index'))

        self.assertContains(response_first_post, "Пост первого поста")
        self.assertEqual(post_one.status_code, 200)

        post_two = self.auth_client.post(
                reverse('new_post'),
                data={"text": "Пост второго поста",
                      "author": self.user,
                      "group": self.group.id},
                follow=True)

        response_second_post = self.auth_client.get(reverse('index'))

        self.assertEqual(post_two.status_code, 200)
        self.assertNotContains(response_second_post, "Пост второго поста")

    def test_follow_and_unfollow_auth_user(self):
        user_1 = User.objects.create_user(
            username="Fedun",
            email="fedun@ya.ru"
        )
        response_follow = self.auth_client.post(
            reverse('profile_follow', kwargs={
                    'username': user_1}),
            data={"user": self.user,
                  "author": user_1},
            follow=True)
        follow_counter_fol = Follow.objects.count()

        self.assertEqual(response_follow.status_code, 200)
        self.assertTrue(response_follow.context['following'])
        self.assertEqual(follow_counter_fol, 1)

        response_unfollow = self.auth_client.post(
            reverse('profile_unfollow', kwargs={
                    'username': user_1}),
            data={"user": self.user,
                  "author": user_1},
            follow=True)

        follow_counter_unfol = Follow.objects.count()
        self.assertEqual(response_unfollow.status_code, 200)
        self.assertFalse(response_unfollow.context['following'])
        self.assertEqual(follow_counter_unfol, 0)

    def test_new_post_follow_and_unfollow(self):
        user_follower = User.objects.create_user(username="Fedun",
                                                 email="fedun@ya.ru")

        response_follow = self.auth_client.post(
            reverse('profile_follow', kwargs={
                    'username': user_follower.username}),
            data={"user": self.user,
                  "author": user_follower},
            follow=True)

        new_post = Post.objects.create(text="Текст нового поста",
                                       author=user_follower,
                                       group=self.group)

        response_post = self.auth_client.post(reverse('follow_index'))
        post_fol = response_post.context['paginator'].object_list.first()

        self.assertEqual(post_fol.text, "Текст нового поста")

        response_unfollow = self.auth_client.post(
            reverse('profile_unfollow', kwargs={
                    'username': user_follower.username}),
            data={"user": self.user,
                  "author": user_follower},
            follow=True)

        post_unfol = response_post.context['paginator'].object_list.first()

        self.assertEqual(post_unfol, None)

    def test_create_comment_auth_and_nonauth_user(self):
        user_1 = User.objects.create_user(username="Fedun",
                                          email="fedun@ya.ru")

        new_post = Post.objects.create(text="Текст нового поста",
                                       author=user_1,
                                       group=self.group)

        response_comment_auth = self.auth_client.post(
            reverse('add_comment', kwargs={
                    'username': user_1.username,
                    'post_id': new_post.id}),
            data={"post": new_post.id,
                  "author": self.user,
                  "text": "Новый коммент авторизованного пользователя"},
            follow=True)
        comment_counter_auth = Comment.objects.count()
        self.assertEqual(response_comment_auth.status_code, 200)
        self.assertEqual(comment_counter_auth, 1)

        response_comment_nonauth = self.nonauth_client.post(
            reverse('add_comment', kwargs={
                    'username': user_1.username,
                    'post_id': new_post.id}),
            data={"post": new_post.id,
                  "author": self.user,
                  "text": "Новый коммент неавторизаванного пользователя"},
            follow=True)

        comment_counter_nonauth = Comment.objects.count()

        self.assertEqual(comment_counter_nonauth, 1)

    def tearDown(self):
        print("Тест выполнен")
