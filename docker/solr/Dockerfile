FROM solr:5.5

USER root
RUN apt-get update && apt-get -y install patch

USER solr
RUN sed -i -e's/^SOLR_HEAP=.*/SOLR_HEAP="4096m"/' /opt/solr/bin/solr.in.sh \
    && sed -i -e's/^log4j.appender.file.MaxFileSize=.*/log4j.appender.file.MaxFileSize=200MB/' /opt/solr/server/resources/log4j.properties

RUN cp -r ./server/solr/configsets/data_driven_schema_configs/conf conf
ADD ./docker/solr/schema.xml \
    ./docker/solr/solrconfig.xml.patch \
    conf/
ADD ./docker/solr/container-scripts/config-diff.sh /opt/docker-solr/scripts/
RUN cd conf/ && patch -p1 < solrconfig.xml.patch
