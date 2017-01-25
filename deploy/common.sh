#!/usr/bin/env bash

case $TERM in
    *xterm*)
        ;&
    *color*)
        color_prompt=yes
        ;;
    *)
        color_prompt=no
        ;;
esac

if [ "$color_prompt" = yes ]; then
    White="[m[K"
    Red="[0;31m[K"
    Green="[0;32m[K"
    Yellow="[0;33mK"
    Blue="[0;34mK"
else
    White=
    Red=
    Green=
    Yellow=
    Blue=
fi
