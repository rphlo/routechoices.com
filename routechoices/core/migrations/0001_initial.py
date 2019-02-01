# Generated by Django 2.1.5 on 2019-02-01 06:39

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import routechoices.core.models
import routechoices.lib
import routechoices.lib.helper
import routechoices.lib.storages


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Club',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aid', models.CharField(default=routechoices.lib.helper.random_key, editable=False, max_length=12, unique=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('modification_date', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('slug', models.CharField(max_length=50, validators=[routechoices.lib.validators.validate_nice_slug])),
                ('admins', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'club',
                'verbose_name_plural': 'clubs'
            },
        ),
        migrations.CreateModel(
            name='Competitor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aid', models.CharField(default=routechoices.lib.helper.random_key, editable=False, max_length=12, unique=True)),
                ('name', models.CharField(max_length=64)),
                ('short_name', models.CharField(blank=True, max_length=32, null=True)),
                ('start_time', models.DateTimeField()),
            ],
            options={
                'verbose_name_plural': 'competitors',
                'ordering': ['start_time'],
                'verbose_name': 'competitor',
            },
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aid', models.CharField(default=routechoices.lib.helper.short_random_key, max_length=12, unique=True)),
            ],
            options={
                'verbose_name_plural': 'devices',
                'ordering': ['aid'],
                'verbose_name': 'device',
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aid', models.CharField(default=routechoices.lib.helper.random_key, editable=False, max_length=12, unique=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('modification_date', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('slug', models.CharField(max_length=50, validators=[routechoices.lib.validators.validate_nice_slug])),
                ('start_date', models.DateTimeField()),
                ('map', models.ImageField(height_field='image_height', storage=routechoices.lib.storages.OverwriteImageStorage(), upload_to=routechoices.core.models.map_upload_path, width_field='image_width')),
                ('image_height', models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ('image_width', models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ('map_corners_coordinates', models.CharField(help_text='Latitude and longitude of map corners separated by commasin following order Top Left, Top right, Bottom Right, Bottom left. eg: 60.519,22.078,60.518,22.115,60.491,22.112,60.492,22.073', max_length=255, validators=[routechoices.lib.validators.validate_corners_coordinates])),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='core.Club')),
            ],
            options={
                'verbose_name_plural': 'events',
                'ordering': ['-start_date'],
                'verbose_name': 'event',
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.FloatField(validators=[routechoices.lib.validators.validate_latitude])),
                ('longitude', models.FloatField(validators=[routechoices.lib.validators.validate_longitude])),
                ('datetime', models.DateTimeField(default=django.utils.timezone.now)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='locations', to='core.Device')),
            ],
            options={
                'verbose_name_plural': 'locations',
                'ordering': ['-datetime', 'device'],
                'verbose_name': 'location',
            },
        ),
        migrations.AddField(
            model_name='competitor',
            name='device',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.Device'),
        ),
        migrations.AddField(
            model_name='competitor',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competitors', to='core.Event'),
        ),
        migrations.AlterUniqueTogether(
            name='event',
            unique_together={('club', 'slug')},
        ),
    ]
