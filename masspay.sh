#!/bin/sh
heroku config -s -a gratipay | ./env/bin/honcho run -e /dev/stdin ./env/bin/python ./bin/masspay.py -i
./env/bin/python ./bin/masspay.py -o
