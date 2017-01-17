#!/usr/bin/env bash

if [ "$1" == "run" ]; then
    ./manage.py treaties_cache
    exec uwsgi config_file
elif [ "$1" == "debug" ]; then
    exec ./manage.py runserver 0.0.0.0:${APP_PORT}
elif [ "$1" == "init" ]; then
    ./manage.py treaties_cache
else
    exec "$@"
fi