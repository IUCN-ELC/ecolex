#!/usr/bin/env bash
# This is meant to end up on the solr image in /opt/docker-solr/scripts
# Execute this running a solr container or in an already running container
# in order to see the diff between current core config and the default config
# (and eventually save this diff to git repo)

# Run with -v for vervose output = debug. Note that this might ruin your diff

# hide stdout and stderr
if [ "$1" == "-v" ]; then
    DEBUG=true
fi
[ "$DEBUG" != true ] && exec 3>&1 >/dev/null 2>&1

rm -rf /tmp/solrconfig.diff.dir
mkdir  -p /tmp/solrconfig.diff.dir/a
mkdir  -p /tmp/solrconfig.diff.dir/b
cp server/solr/configsets/data_driven_schema_configs/conf/solrconfig.xml /tmp/solrconfig.diff.dir/a
cp server/solr/ecolex/conf/solrconfig.xml /tmp/solrconfig.diff.dir/b
cd /tmp/solrconfig.diff.dir

# restore stdout to output the diff
[ "$DEBUG" != true ] && exec 1>&3
diff -wu5 a/solrconfig.xml b/solrconfig.xml

[ "$DEBUG" != true ] && exec 3>&1 >/dev/null 2>&1
cd
rm -rf /tmp/solrconfig.diff.dir/
