#!/usr/bin/env bash
# Run this command to init the maria db container right from your own, remote machine
# Make sure you have environment vars target the proper machine and build
# We need solr service running for the init to take place

echo Connecting with user $EDW_MACHINE_USER and host $EDW_MACHINE_HOST
echo Running docker-compose on remote from dir $EDW_MACHINE_DIR
echo Make sure you have one of MYSQL_ROOT_PASSWORD, MYSQL_ALLOW_EMPTY_PASSWORD and MYSQL_RANDOM_ROOT_PASSWORD env vars defined
echo Make sure you have ecolex DATABASE vars defined, especially, for docker-compose runs, EDW_MYSQL_DATABASE, EDW_MYSQL_USER and EDW_MYSQL_PASSWORD

ssh -q -t $EDW_MACHINE_USER@$EDW_MACHINE_HOST "cd $EDW_MACHINE_DIR || exit 1 ;\
docker-compose stop >/dev/null 2>&1 || true ;\
docker stop mysql_db_creator >/dev/null 2>&1 || true ;\
docker-compose run --name=mysql_db_creator -d maria mysqld --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci $@ &&\
echo Sleeping for 25 seconds to make sure db is created in the background ;\
sleep 25 ;\
docker logs mysql_db_creator ;\
docker stop mysql_db_creator >/dev/null 2>&1 || true ;\
docker rm mysql_db_creator >/dev/null 2>&1 || true ;\
"
