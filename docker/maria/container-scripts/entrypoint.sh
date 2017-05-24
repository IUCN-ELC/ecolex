#!/usr/bin/env bash

# overwrite mysql config here at container start using passed environment; make sure you escape regex elements that shell might interpret.
# sed -i -e"s/x/${VAR}/" /etc/mysql/my.cnf
sed -i -e"s/^query_cache_size.*=.*/query_cache_size = ${EDW_RUN_MARIA_query_cache_size}/" /etc/mysql/my.cnf
sed -i -e"s/^max_connections.*/max_connections = ${EDW_RUN_MARIA_max_connections}/" /etc/mysql/my.cnf
sed -i -e"s/^max_allowed_packet.*/max_allowed_packet = ${EDW_RUN_MARIA_max_allowed_packet}/" /etc/mysql/my.cnf
sed -i -e"s/^tmp_table_size.*/tmp_table_size = ${EDW_RUN_MARIA_tmp_table_size}/" /etc/mysql/my.cnf
sed -i -e"s/^max_heap_table_size.*/max_heap_table_size = ${EDW_RUN_MARIA_max_heap_table_size}/" /etc/mysql/my.cnf
sed -i -e"s/^query_cache_limit.*/query_cache_limit = ${EDW_RUN_MARIA_query_cache_limit}/" /etc/mysql/my.cnf
sed -i -e"s/^innodb_buffer_pool_size.*/innodb_buffer_pool_size = ${EDW_RUN_MARIA_innodb_buffer_pool_size}/" /etc/mysql/my.cnf

sed -i -e"s/^#slow_query_log.*/slow_query_log = ${EDW_RUN_MARIA_slow_query_log}/" /etc/mysql/my.cnf

# pass on whatever was meant for original solr docker-entrypoint.sh to receive
exec docker-entrypoint.sh "$@"
