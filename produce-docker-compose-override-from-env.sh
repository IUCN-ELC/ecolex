#!/usr/bin/env bash

env_file=${1:-.env}
env $(xargs < $env_file) envsubst <docker-compose.override.template >docker-compose.override.yml