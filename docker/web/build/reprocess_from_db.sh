#!/usr/bin/env bash

$ECOLEX_HOME/ecolex/manage.py import legislation --reindex
$ECOLEX_HOME/ecolex/manage.py import legislation --update-text

$ECOLEX_HOME/ecolex/manage.py import literature --reindex
$ECOLEX_HOME/ecolex/manage.py import literature --update-text

$ECOLEX_HOME/ecolex/manage.py import treaty --reindex
$ECOLEX_HOME/ecolex/manage.py import treaty --update-text
$ECOLEX_HOME/ecolex/manage.py import treaty --update-status

$ECOLEX_HOME/ecolex/manage.py import decision --reindex