#!/bin/sh
heroku config -s | honcho -e /dev/stdin run ./env/bin/python ./bin/masspay.py -i
./bin/masspay.py -o
