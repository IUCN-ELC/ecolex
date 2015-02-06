#!/bin/bash

echo "Check if solr is on..."
SOLR_PID=$(ps aux | grep start.jar | grep java | tr -s ' ' | cut -d' ' -f2)
echo $SOLR_PID
if [ "$SOLR_PID" == "" ]; then
    echo "No solr found"
else
    echo "Solr $SOLR_PID found. Killing"
    kill -9 $SOLR_PID
fi

echo "Starting a new instance..."
cd ./solr-*/example
java -DzkHost=localhost:2181 -jar start.jar &> /dev/null & 

echo "Done"
