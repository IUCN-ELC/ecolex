#!/usr/bin/env bash

#echo Connecting with user $EDW_MACHINE_USER and host $EDW_MACHINE_HOST
#echo Running docker-compose on remote from dir $EDW_MACHINE_DIR
#docker-compose exec solr config-diff.sh

#ssh $EDW_MACHINE_USER@$EDW_MACHINE_HOST << _eof_
#pwd
#docker-compose ps
#_eof_

ssh -q -t $EDW_MACHINE_USER@$EDW_MACHINE_HOST "cd ${EDW_MACHINE_DIR} &&\
docker-compose exec solr config-diff.sh"
