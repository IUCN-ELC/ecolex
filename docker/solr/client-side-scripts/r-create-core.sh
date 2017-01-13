#!/usr/bin/env bash
# Run this command to create a core based on the default solr
# server/solr/configsets/data_driven_schema_configs/conf overridden with the schema and config
# from this directory
# Make sure solr is not running when doing this as this needs to start a solr of its own
# also you should stop this container afterwards as it will continue to run a solr instance after core creation

echo Connecting with user $ECOLEX_USER and host $ECOLEX_HOST
echo Running docker-compose on remote from dir $ECOLEX_DIR

ssh -q -t $ECOLEX_USER@$ECOLEX_HOST "cd $ECOLEX_DIR &&\
docker-compse stop solr || true ;\
docker-compose run --rm -d solr solr-create -c ecolex -d conf &&\
echo sleeping for 60 seconds to make sure the core gets created in the background ;\
sleep 60 ;\
docker-compose stop solr || true ;\
docker-compose up -d
"
