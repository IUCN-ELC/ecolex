#!/usr/bin/env bash

#echo Connecting with user $ECOLEX_USER and host $ECOLEX_HOST
#echo Running docker-compose on remote from dir $ECOLEX_DIR
#docker-compose exec solr config-diff.sh

#ssh $ECOLEX_USER@$ECOLEX_HOST << _eof_
#pwd
#docker-compose ps
#_eof_

ssh -q -t $ECOLEX_USER@$ECOLEX_HOST "cd ${ECOLEX_DIR} &&\
docker-compose exec solr config-diff.sh"
