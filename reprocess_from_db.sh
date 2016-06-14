#!/bin/sh

export SOLR_URI=http://solr:8983/solr/ecolex

/usr/local/bin/python /ecolex/manage.py import legislation --reindex
/usr/local/bin/python /ecolex/manage.py import legislation --update-text
