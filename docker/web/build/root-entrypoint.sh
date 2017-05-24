#!/usr/bin/env bash

# We are still root here

# Start cron in background
/usr/sbin/cron

exec gosu $USER:$USER entrypoint.sh "$@"
