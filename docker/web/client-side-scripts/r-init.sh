#!/usr/bin/env bash
# Run this command to init the web container right from your own, remote machine
# Make user you have environment vars target the proper machine and build
# We need solr service running for the init to take place

echo Connecting with user $EDW_MACHINE_USER and host $EDW_MACHINE_HOST
echo Running docker-compose on remote from dir $EDW_MACHINE_DIR

ssh -q -t $EDW_MACHINE_USER@$EDW_MACHINE_HOST "cd $EDW_MACHINE_DIR || exit 1 ;\
docker-compose stop >/dev/null 2>&1 || true ;\
docker-compose run --rm web init $@;\
docker-compose stop || true \;
"
