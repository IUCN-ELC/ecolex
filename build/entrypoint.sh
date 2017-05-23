#!/usr/bin/env bash

init() {
    ../manage.py migrate
    ../manage.py collectstatic --noinput
}

init_bare() {
    init
    ../manage.py loaddata ecolex/fixtures/initial_data.json
    if [ "$1" = "solr" ]; then
        cp ecolex/local_settings.initial_example ecolex/local_settings.py
        import_updater.sh
        rm ecolex/local_settings.py
    fi
}

wait_sql() {
    while ! nc -z maria 3306; do
        echo "Waiting for MySQL server maria:3306 ..."
        sleep 1
    done
}

install_crontab() {
    # with this method we can keep any kind of env var in crontab and it will work
    # we exclude some for the horror they are
    env | grep -v 'LS_COLORS\|no_proxy' > $ECOLEX_HOME/ecolex_crontab_with_env
    cat $ECOLEX_HOME/ecolex.crontab >> $ECOLEX_HOME/ecolex_crontab_with_env
    crontab -u $USER $ECOLEX_HOME/ecolex_crontab_with_env
}

if [ "$1" == "run" ]; then
    wait_sql
    install_crontab
    init
    exec gunicorn -w1 --bind=0.0.0.0:8000 --access-logfile=- --error-logfile=- ecolex.wsgi:application
elif [ "$1" == "debug" ]; then
    wait_sql
    exec ./manage.py runserver 0.0.0.0:8000
elif [ "$1" == "init" ]; then
    shift
    wait_sql
    init_bare "$@"
else
    exec "$@"
fi