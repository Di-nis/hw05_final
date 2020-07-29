# Generated by Django 2.2.9 on 2020-07-27 12:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0003_auto_20200727_1318'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='posts/'),
        ),
        migrations.AlterField(
            model_name='post',
            name='group',
            field=models.ForeignKey(blank=True, help_text='Выберите сообщество', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='group_posts', to='posts.Group', verbose_name='Наименование сообщества'),
        ),
    ]
