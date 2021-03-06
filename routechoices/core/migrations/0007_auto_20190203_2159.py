# Generated by Django 2.1.5 on 2019-02-03 21:59

from django.db import migrations, models
import routechoices.lib.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20190203_2044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='End Date (UTC)'),
        ),
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.CharField(db_index=True, help_text='This the text that will be used in the urls of your events', max_length=50, validators=[routechoices.lib.validators.validate_nice_slug]),
        ),
        migrations.AlterField(
            model_name='event',
            name='start_date',
            field=models.DateTimeField(verbose_name='Start Date (UTC)'),
        ),
    ]
