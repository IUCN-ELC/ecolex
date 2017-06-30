#!/usr/bin/env bash

# We are still root here

# Start cron in background
/usr/sbin/cron
service sendmail start

exec gosu $USER:$USER entrypoint.sh "$@"
