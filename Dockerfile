FROM python:3.4
RUN apt-get -y update
RUN apt-get -y install cron


RUN mkdir /ecolex
WORKDIR /ecolex
ADD . /ecolex

RUN crontab crontab.example
RUN /etc/init.d/cron start
RUN pip install -r requirements.txt

ENV APP_PORT 8000
EXPOSE ${APP_PORT}
CMD bash -c "python manage.py treaties_cache && python manage.py runserver 0.0.0.0:${APP_PORT}"
