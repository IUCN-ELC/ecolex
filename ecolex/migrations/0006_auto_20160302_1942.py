# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ecolex', '0005_auto_20160219_1805'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documenttext',
            name='doc_id',
            field=models.CharField(max_length=128, db_index=True),
            preserve_default=True,
        ),
    ]
