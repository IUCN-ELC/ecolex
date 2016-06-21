# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('ecolex', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='documenttext',
            old_name='index_datetime',
            new_name='created_datetime',
        ),
        migrations.AddField(
            model_name='documenttext',
            name='parsed_data',
            field=models.TextField(blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='documenttext',
            name='status',
            field=models.CharField(max_length=32, choices=[('failed', 'failed'), ('success', 'success'), ('retry', 'retry')], default='success'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='documenttext',
            name='updated_datetime',
            field=models.DateTimeField(default=datetime.datetime(2016, 2, 10, 14, 4, 9, 168613, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='documenttext',
            name='doc_size',
            field=models.IntegerField(blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='documenttext',
            name='text',
            field=models.TextField(blank=True, null=True),
            preserve_default=True,
        ),
    ]
