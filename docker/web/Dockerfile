FROM python:3.4
RUN apt-get -y update &&\
    apt-get -y --no-install-recommends install vim sudo
#RUN rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos '' --shell /bin/false web &&\
    adduser web sudo &&\
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# override at command line docker build --build-arg APP_PORT=8001
ARG APP_PORT=8000

ENV THIS_HOME=/home/web \
    PATH=/home/web/bin:$PATH \
    APP_PORT=$APP_PORT

RUN mkdir -p $THIS_HOME/ecolex &&\
    mkdir -p $THIS_HOME/bin

ADD requirements.txt \
    requirements-dep.txt \
    $THIS_HOME/ecolex/
ADD docker/web/entrypoint.sh \
    $THIS_HOME/bin/

WORKDIR $THIS_HOME/ecolex
RUN pip install -r requirements.txt

RUN chown -R web:web $THIS_HOME

EXPOSE $APP_PORT

USER web
ENTRYPOINT ["entrypoint.sh"]
CMD ["run"]
