# Generated by Django 5.1.7 on 2025-03-15 09:44

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AudioFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='音訊檔案的標題或名稱', max_length=255, verbose_name='標題')),
                ('description', models.TextField(blank=True, help_text='音訊檔案的簡要描述（選填）', verbose_name='描述')),
                ('file', models.FileField(help_text='支援的格式：MP3, WAV, OGG, M4A, FLAC', upload_to='audio_files/%Y/%m/', verbose_name='音訊檔案')),
                ('format', models.CharField(blank=True, max_length=10, verbose_name='檔案格式')),
                ('duration', models.FloatField(blank=True, null=True, verbose_name='時長（秒）')),
                ('file_size', models.PositiveIntegerField(blank=True, null=True, verbose_name='檔案大小（位元組）')),
                ('sample_rate', models.PositiveIntegerField(blank=True, null=True, verbose_name='採樣率 (Hz)')),
                ('channels', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='聲道數')),
                ('processing_status', models.CharField(choices=[('pending', '等待處理'), ('processing', '處理中'), ('completed', '已完成'), ('failed', '處理失敗')], default='pending', max_length=20, verbose_name='處理狀態')),
                ('processing_message', models.TextField(blank=True, verbose_name='處理訊息')),
                ('processing_method', models.CharField(blank=True, help_text='使用的轉錄引擎或模型', max_length=50, verbose_name='處理方法')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='處理完成時間')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audio_files', to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '音訊檔案',
                'verbose_name_plural': '音訊檔案',
                'ordering': ['-created_at'],
            },
        ),
    ]
