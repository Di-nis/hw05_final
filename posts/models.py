import textwrap

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=40, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        help_text="Введите текст",
        verbose_name="Текст"
    )
    pub_date = models.DateTimeField("date published", auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="posts")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL,
                              related_name="group_posts",
                              blank=True, null=True,
                              help_text="Выберите сообщество",
                              verbose_name="Наименование сообщества")
    image = models.ImageField(upload_to='posts/', blank=True, null=True,
                              help_text="Загрузите изображение",
                              verbose_name="Изображение")

    def __str__(self):
        return textwrap.shorten(self.text, width=300)

    class Meta:
        ordering = ["-pub_date"]


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE,
                             related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="comments")
    text = models.TextField(help_text="Введите комментарий",
                            verbose_name="Комментарий")
    created = models.DateTimeField("date published", auto_now_add=True)


class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name="follower")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="following")

    class Meta:
        unique_together = ['user', 'author']
