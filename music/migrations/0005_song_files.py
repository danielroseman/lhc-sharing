# Generated by Django 4.2.15 on 2024-09-01 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0004_alter_file_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='files',
            field=models.TextField(blank=True, default='[]'),
            preserve_default=False
        ),
    ]
