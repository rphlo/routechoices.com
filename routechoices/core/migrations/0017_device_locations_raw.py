# Generated by Django 2.2.11 on 2020-03-12 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20190607_1818'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='locations_raw',
            field=models.TextField(blank=True, null=True),
        ),
    ]
