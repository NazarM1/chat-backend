# Generated by Django 5.1.4 on 2025-02-09 12:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_phasecontent_phase'),
    ]

    operations = [
        migrations.AddField(
            model_name='phasecontent',
            name='status',
            field=models.CharField(choices=[('read', 'Read'), ('unread', 'Unread')], default='unread', max_length=10),
        ),
        migrations.AddField(
            model_name='phasecontent',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
