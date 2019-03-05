#!/usr/bin/env sh

find .. ! \( -name "." -o -name ".." -o -name "source" -o -path "*/source/*" \) -exec rm -rf "{}" +

