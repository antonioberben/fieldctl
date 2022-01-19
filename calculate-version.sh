#!/bin/sh

type="${1:-rc}"
current_version=$(cat version-base.txt)
echo "$current_version-$type.$(date '+%Y%m%d.%H%M')" > version.txt