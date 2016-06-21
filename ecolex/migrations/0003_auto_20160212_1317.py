# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ecolex', '0002_auto_20160210_1404'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documenttext',
            name='status',
            field=models.CharField(choices=[('indexed', 'indexed'), ('full_index', 'full_index'), ('index_fail', 'index_fail'), ('full_index_fail', 'full_index_fail')], max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='documenttext',
            name='url',
            field=models.CharField(blank=True, null=True, max_length=128),
            preserve_default=True,
        ),
    ]
