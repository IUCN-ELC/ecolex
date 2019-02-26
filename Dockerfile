FROM python:3.6-slim

# roles:
#   front - publishes ports to the world; this depends on run/docker-compose though...
#   cron - runs cron daemon
LABEL maintainer="ecolex@eaudeweb.ro" \
      roles="front,cron" \
      name="web"

ENV ECOLEX_HOME=/home/web \
    PATH=/home/web/bin:$PATH \
    EDW_RUN_WEB_PORT=8000 

RUN apt-get -y update &&\
    apt-get -y --no-install-recommends install \
    vim \
    netcat-traditional \
    git \
    libmariadb-client-lgpl-dev \
    gcc \
    libc-dev-bin \
    libc6-dev \
    make \
    patch \
    cron \
    curl \
    libyajl2 \
    ssmtp \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/mariadb_config /usr/bin/mysql_config &&\
    mkdir -p $ECOLEX_HOME/ecolex \
             /www_static \
             $ECOLEX_HOME/bin &&\
    echo "ECOLEX_HOME=${ECOLEX_HOME}" >> /etc/environment



# Add as few files of possible, we want to cache pip install step for good
COPY docker/docker-entrypoint.sh \
    docker/import_updater.sh \
    docker/reprocess_from_db.sh \
    $ECOLEX_HOME/bin/

COPY docker/ecolex.crontab \
    $ECOLEX_HOME/

# Every time you change the value of this variable the cache will be skipped from the next RUN step further
#ARG EDW_ECOLEX_VER
#RUN echo $EDW_ECOLEX_VER
COPY requirements.txt \
    requirements-dep.txt \
    manage.py \
    $ECOLEX_HOME/ecolex/

WORKDIR $ECOLEX_HOME/ecolex
RUN pip install -r requirements-dep.txt

COPY ecolex $ECOLEX_HOME/ecolex/ecolex
# no changes to volume are persistent after declaring it


VOLUME ["/www_static", "${ECOLEX_HOME}/ecolex/logs"]

# USER web # use gosu in the entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["run"]
