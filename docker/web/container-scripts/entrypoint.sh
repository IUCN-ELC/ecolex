#!/usr/bin/env bash

_init() {
    ./manage.py migrate
    ./manage.py collectstatic --noinput
}

_init_bare() {
    _init
    ./manage.py loaddata ecolex/fixtures/initial_data.json
    if [ "$1" != "skip_solr" ]; then
        cp ecolex/local_settings.initial_example ecolex/local_settings.py
        import_updater.sh
        rm ecolex/local_settings.py
    fi
}
if [ "$1" == "run" ]; then
    _init
    exec uwsgi config_file
elif [ "$1" == "debug" ]; then
    exec ./manage.py runserver 0.0.0.0:$EDW_WEB_PORT
elif [ "$1" == "init" ]; then
    shift
    _init_bare "$@"
else
    exec "$@"
fi