# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ecolex', '0003_auto_20160212_1317'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documenttext',
            name='updated_datetime',
            field=models.DateTimeField(auto_now=True),
            preserve_default=True,
        ),
    ]
