#!/bin/sh

export WEB_SOLR_URI=http://solr:8983/solr/ecolex

/usr/local/bin/python /ecolex/manage.py import legislation --reindex
/usr/local/bin/python /ecolex/manage.py import legislation --update-text

/usr/local/bin/python /ecolex/manage.py import literature --reindex
/usr/local/bin/python /ecolex/manage.py import literature --update-text

/usr/local/bin/python /ecolex/manage.py import treaty --reindex
/usr/local/bin/python /ecolex/manage.py import treaty --update-text
/usr/local/bin/python /ecolex/manage.py import treaty --update-status

/usr/local/bin/python /ecolex/manage.py import decision --reindex
