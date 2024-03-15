#!/usr/bin/env bash

# outdated, only for manual execution
# $PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import legislation --reindex
# $PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import legislation --update-text

$PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import literature --reindex
$PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import literature --update-text

$PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import treaty --reindex
$PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import treaty --update-text
$PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import treaty --update-status

$PYTHONPATH/python $ECOLEX_HOME/ecolex/manage.py import decision --reindex