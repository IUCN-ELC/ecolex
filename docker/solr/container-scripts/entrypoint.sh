#!/usr/bin/env bash

sed -i -e"s/^SOLR_HEAP=.*\$/SOLR_HEAP=\"${EDW_RUN_SOLR_HEAP_MB:-4096}m\"/" /opt/solr/bin/solr.in.sh
sed -i -e"s/^log4j.appender.file.MaxFileSize=.*/log4j.appender.file.MaxFileSize=${EDW_RUN_SOLR_LOG_MB:-200}MB/" /opt/solr/server/resources/log4j.properties

# pass on whatever was meant for original solr docker-entrypoint.sh to receive
exec docker-entrypoint.sh "$@"
