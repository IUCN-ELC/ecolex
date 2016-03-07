# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ecolex', '0004_auto_20160212_1322'),
    ]

    operations = [
        migrations.AddField(
            model_name='documenttext',
            name='doc_type',
            field=models.CharField(max_length=16, default='legislation'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='documenttext',
            name='status',
            field=models.CharField(choices=[('indexed', 'indexed'), ('full_index', 'full_index'), ('index_fail', 'index_fail')], max_length=32),
            preserve_default=True,
        ),
    ]
