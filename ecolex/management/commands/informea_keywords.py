import logging
import rdflib
import json

from collections import defaultdict

from django.core.management.base import BaseCommand

from ecolex.management.commands.logging import LOG_DICT

logging.config.dictConfig(LOG_DICT)
import_logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Custom command for creating mapping between InforMEA and ECOLEX keywords."""
    help = 'Convert mapping of keywords from RDF'

    def handle(self, *args, **options):
        informea = rdflib.Graph()
        informea.load('https://informea.org/sites/default/files/export/informea.rdf')
        ecolex = rdflib.Graph()
        ecolex.load('https://informea.org/sites/default/files/export/ecolex.rdf')
        preflabel_prop = rdflib.term.URIRef('http://www.w3.org/2008/05/skos-xl#prefLabel')
        literal_prop = rdflib.term.URIRef('http://www.w3.org/2008/05/skos-xl#literalForm')

        mappings = defaultdict(list)
        for s, p, o in informea.triples((None, rdflib.namespace.SKOS.relatedMatch, None)):
            if o.startswith('http://www.ecolex.org/keywords'):
                prefLabel_informea = informea.value(subject=s, predicate=preflabel_prop)
                informea_keyword = informea.value(subject=prefLabel_informea, predicate=literal_prop)
                prefLabel_ecolex = ecolex.value(subject=o, predicate=preflabel_prop)
                ecolex_keyword = ecolex.value(subject=prefLabel_ecolex, predicate=literal_prop)
                # xml:lang is ignored
                mappings[informea_keyword.value].append(ecolex_keyword.value)

        with open('informea_ecolex.json', 'w', encoding='utf8') as json_file:
            json.dump(mappings, json_file, ensure_ascii=False, sort_keys=True, indent=2)
