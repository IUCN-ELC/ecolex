from django.db import models


class DocumentText(models.Model):

    doc_id = models.CharField(max_length=128, null=False, blank=False)
    url = models.CharField(max_length=128, null=False, blank=False)
    text = models.TextField(null=False, blank=False)
    doc_size = models.IntegerField(null=False, blank=False)
    index_datetime = models.DateTimeField(auto_now_add=True, auto_now=False)

    def __unicode__(self):
        return self.doc_id
