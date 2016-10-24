#!/bin/sh

set -e
cd "`dirname $0`/.."

wget https://registry.npmjs.com/-/all
./env/bin/python ./bin/npm.py serialize all > serialized
./env/bin/python ./bin/npm.py upsert serialized
