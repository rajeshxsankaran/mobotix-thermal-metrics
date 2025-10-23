#!/bin/bash -e

docker build --pull -f Dockerfile \
        -t mobotix-thermal-metrics:latest .
