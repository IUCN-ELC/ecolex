#!/usr/bin/env bash
# Run this command to create a core based on the default solr
# server/solr/configsets/data_driven_schema_configs/conf overridden with the schema and config
# from this directory
# Make sure solr is not running when doing this as this needs to start a solr of its own
# also you should stop this container afterwards as it will continue to run a solr instance after core creation
# (this is the reason we do the annoying wait at the end - if we run create-core in foreground,
#  it will stay forever after the core creation as regular solr service)

echo Connecting with user $EDW_MACHINE_USER and host $EDW_MACHINE_HOST
echo Running docker-compose on remote from dir $EDW_MACHINE_DIR

ssh -q -t $EDW_MACHINE_USER@$EDW_MACHINE_HOST "cd $EDW_MACHINE_DIR &&\
docker-compose stop solr >/dev/null 2>&1 || true ;\
docker stop solr_core_creator >/dev/null 2>&1 || true ;\
docker-compose run --name=solr_core_creator -d solr solr-create -c ecolex -d conf &&\
echo sleeping for 30 seconds to make sure the core gets created in the background ;\
sleep 30 ;\
docker stop solr_core_creator >/dev/null 2>&1 || true ;\
docker rm solr_core_creator >/dev/null 2>&1 || true ;\
"
