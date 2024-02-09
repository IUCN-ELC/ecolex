#!/usr/bin/env bash

/usr/sbin/cron

init() {
    ./manage.py migrate
    ./manage.py collectstatic --noinput
}

wait_sql() {
    while ! nc -z $MYSQL_HOST 3306; do
        echo "Waiting for MySQL server $MYSQL_HOST:3306 ..."
        sleep 1
    done
}

wait_solr() {
    while ! nc -z $SOLR_HOST $SOLR_PORT; do
        echo "Waiting for Solr server $SOLR_HOST:$SOLR_PORT ..."
        sleep 1
    done

}

install_crontab() {
    echo "Installing crontab"
    printenv | sed 's/^\(.*\)$/export \1/g' | grep -E "(EDW|MYSQL|ECOLEX)" &> $ECOLEX_HOME/.bashrc
    chmod 755 $ECOLEX_HOME/.bashrc
    crontab $ECOLEX_HOME/ecolex.crontab
}

if [ "$1" == "run" ]; then
    wait_sql
    wait_solr
    install_crontab
    init
    exec gunicorn --bind=0.0.0.0:$EDW_RUN_WEB_PORT --access-logfile=- --error-logfile=- ecolex.wsgi:application
elif [ "$1" == "init_dev" ]; then
    wait_sql
    wait_solr
    ./manage.py migrate
    ./manage.py loaddata ecolex/fixtures/initial_data.json
    exec ./manage.py runserver 0.0.0.0:$EDW_RUN_WEB_PORT
elif [ "$1" == "debug" ]; then
    wait_sql
    wait_solr
    exec ./manage.py runserver 0.0.0.0:$EDW_RUN_WEB_PORT
else
    exec "$@"
fi
