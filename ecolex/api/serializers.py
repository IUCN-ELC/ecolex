from functools import lru_cache
from rest_framework.serializers import Serializer
from rest_framework import fields


class BaseResultSerializer(Serializer):
    id = fields.CharField()
    type = fields.CharField()
    source = fields.CharField()
    title = fields.CharField()
    #abstract = fields.CharField()
    #summary = fields.CharField()
    language = fields.CharField(required=False)
    country = fields.CharField(required=False)
    date = fields.DateField()
    subjects = fields.ListField()
    keywords = fields.ListField()


class LegislationResultSerializer(BaseResultSerializer):
    date = fields.CharField() # temporary


class LiteratureResultSerializer(BaseResultSerializer):
    pass


class TreatyResultSerializer(BaseResultSerializer):
    pass


class CourtDecisionResultSerializer(BaseResultSerializer):
    pass


class SearchResultSerializer(BaseResultSerializer):
    _SERIALIZER_MAPPING = {
        'legislation': LegislationResultSerializer,
        'literature': LiteratureResultSerializer,
        'treaty': TreatyResultSerializer,
        'court_decision': CourtDecisionResultSerializer,
    }

    @lru_cache(maxsize=0)
    def _get_serializer_instance(self, for_type):
        return self._SERIALIZER_MAPPING[for_type]()

    def to_representation(self, instance):
        try:
            s = self._get_serializer_instance(instance.type)
        except KeyError:
            return super().to_representation(instance)
        else:
            return s.to_representation(instance)


class SearchFacetSerializer(Serializer):
    item = fields.CharField()
    count = fields.IntegerField()
