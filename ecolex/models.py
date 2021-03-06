from django.db import models


class DocumentText(models.Model):

    INDEXED = 'indexed'  # Indexed, but pdf not indexed
    FULL_INDEXED = 'full_index'  # Indexed and pdf indexed
    INDEX_FAIL = 'index_fail'  # Failed to index during FAO service call (solr related)
    FULL_INDEX_FAIL = 'full_index_fail'  # Failed to download/parse the attachment

    STATUS_TYPES = (
        (INDEXED, INDEXED),
        (FULL_INDEXED, FULL_INDEXED),
        (INDEX_FAIL, INDEX_FAIL),
        (FULL_INDEX_FAIL, FULL_INDEX_FAIL),
    )

    doc_id = models.CharField(db_index=True, max_length=128, null=False, blank=False)
    doc_type = models.CharField(max_length=16, null=False, blank=False)
    url = models.CharField(max_length=256, null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    parsed_data = models.TextField(null=True, blank=True)
    doc_size = models.IntegerField(null=True, blank=True)
    created_datetime = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated_datetime = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=32, choices=STATUS_TYPES,
                              null=False, blank=False)

    def __str__(self):
        return self.doc_id + ' ' + self.status

    class Meta:
        index_together = [
            ("doc_type", "status"),
        ]


class StaticContent(models.Model):

    name = models.CharField(max_length=64, null=False, blank=False,
                            unique=True)
    body_en = models.TextField(null=False, blank=False)
    body_es = models.TextField()
    body_fr = models.TextField()

    def __str__(self):
        return self.name
