Scripts found in here are to be copied inside tha image.
For solr the scripts under /opt/docker-solr/scripts will be reachable from PATH
Thus this destination should be used when copying these scripts
one can run them, from a remote, client machine afterwards with
ssh -q -t $EDW_MACHINE_USER@$EDW_MACHINE_HOST "cd $EDW_MACHINE_DIR &&\
docker-compose exec solr <name of the script originated from this dir>"

Please see exemples of running these scripts remotely in client-side-scripts

