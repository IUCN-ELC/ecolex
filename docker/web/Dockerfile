FROM python:3.4
RUN apt-get -y update &&\
    apt-get -y --no-install-recommends install vim sudo
#RUN rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos '' --shell /bin/false web &&\
    adduser web sudo &&\
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

ENV THIS_HOME=/home/web \
    PATH=/home/web/bin:$PATH \
    EDW_WEB_PORT=8000

RUN mkdir -p $THIS_HOME/ecolex &&\
    mkdir -p $THIS_HOME/bin

# Add as few files of possible, we want to cache pip install step for good
ADD requirements.txt \
    requirements-dep.txt \
    $THIS_HOME/ecolex/

ADD docker/web/container-scripts/entrypoint.sh \
    docker/web/container-scripts/import_updater.sh \
    $THIS_HOME/bin/

WORKDIR $THIS_HOME/ecolex
RUN pip install -r requirements-dep.txt

# Every time you change the value of this variable the cache will be skipped from the next RUN step further
ARG EDW_ECOLEX_VER
RUN echo $EDW_ECOLEX_VER
# Add all the source files. Use a volume when monting if you want to see live changes. Prod should be frozen
# TODO this should be done through git. Any debris one has on his work dir should not make it into the image.
ADD . $THIS_HOME/ecolex/
RUN chown -R web:web $THIS_HOME

EXPOSE $EDW_WEB_PORT

USER web
ENTRYPOINT ["entrypoint.sh"]
CMD ["run"]
