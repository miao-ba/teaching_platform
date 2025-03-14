# Generated by Django 5.1.7 on 2025-03-14 21:45

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_type', models.CharField(choices=[('audio_transcription', '音訊轉錄'), ('speaker_identification', '講者辨識'), ('summary_generation', '摘要生成'), ('content_generation', '內容生成'), ('rag_search', '知識檢索')], max_length=50, verbose_name='服務類型')),
                ('operation', models.CharField(max_length=100, verbose_name='操作描述')),
                ('resource_id', models.IntegerField(blank=True, null=True, verbose_name='資源 ID')),
                ('tokens_used', models.IntegerField(default=0, verbose_name='使用 Token 數量')),
                ('model_name', models.CharField(blank=True, max_length=100, verbose_name='模型名稱')),
                ('audio_duration', models.FloatField(blank=True, null=True, verbose_name='音訊時長(秒)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_logs', to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '使用日誌',
                'verbose_name_plural': '使用日誌',
                'ordering': ['-created_at'],
            },
        ),
    ]
