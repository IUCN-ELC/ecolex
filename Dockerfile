FROM python:3
RUN apt-get -y update

RUN mkdir /ecolex
WORKDIR /ecolex
ADD . /ecolex

RUN pip install -r requirements.txt

ENV APP_PORT 8000
EXPOSE ${APP_PORT}
CMD bash -c "python manage.py treaties_cache && python manage.py runserver 0.0.0.0:${APP_PORT}"
