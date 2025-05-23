# Generated by Django 5.0.6 on 2025-04-13 06:19

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Blog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=250, unique_for_date='published_at')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('is_published', models.BooleanField(default=False)),
                ('featured_image', models.ImageField(blank=True, null=True, upload_to='blog_images/')),
                ('views', models.PositiveIntegerField(default=0)),
                ('deleted', models.BooleanField(default=False)),
                ('draft', models.BooleanField(default=False)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blog_author', to=settings.AUTH_USER_MODEL)),
                ('categories', models.ManyToManyField(related_name='blog_categories', to='accounts.techcategory')),
            ],
            options={
                'ordering': ['-published_at'],
                'indexes': [models.Index(fields=['-published_at'], name='blogs_blog_publish_49fd4f_idx'), models.Index(fields=['slug'], name='blogs_blog_slug_d0bba8_idx')],
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('object_id', models.PositiveIntegerField()),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blog_comments', to=settings.AUTH_USER_MODEL)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blog_reactions', to='contenttypes.contenttype')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='blogs.comment')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['content_type', 'object_id'], name='blogs_comme_content_975180_idx')],
            },
        ),
        migrations.CreateModel(
            name='Reaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('reaction_type', models.CharField(choices=[('clap', '👏'), ('like', '👍'), ('dislike', '👎'), ('heart', '❤️'), ('rocket', '🚀')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blog_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [models.Index(fields=['content_type', 'object_id'], name='blogs_react_content_9ddd0a_idx')],
                'unique_together': {('user', 'content_type', 'object_id')},
            },
        ),
    ]
