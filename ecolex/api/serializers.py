from rest_framework.serializers import Serializer
from rest_framework import fields


class SearchResultSerializer(Serializer):
    id = fields.CharField()
    type = fields.CharField()
    source = fields.CharField()
    title = fields.CharField()
    #abstract = fields.CharField()
    #summary = fields.CharField()
    #language = fields.CharField(required=False)
    country = fields.CharField(required=False)
    date = fields.DateField()
    subjects = fields.ListField()
    keywords = fields.ListField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['hmm'] = 'hmm?'
