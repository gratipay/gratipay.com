#!/bin/sh
# This is a script to run under the Heroku Scheduler add-on to periodically
# sync our database with the npm registry.

set -e
cd "`dirname $0`/.."

# Install dependencies.
# =====================

# cmake - required by ...
curl https://cmake.org/files/v3.6/cmake-3.6.2-Linux-x86_64.tar.gz > cmake.tgz
echo '5df4b69d9e85093ae78b1070d5cb9f824ce0bdd02528948c3f6a740e240083e5  cmake.tgz' \
     | sha256sum -c /dev/stdin --status
tar zxf cmake.tgz
PATH=/app/cmake-3.6.2-Linux-x86_64/bin:$PATH

# yajl
git clone https://github.com/lloyd/yajl.git
cd yajl
git checkout 2.1.0
./configure -p /app/.heroku/python
make install
cd ..

# python
pip install ijson==2.3.0
pip install -e .


# Sync with npm.
# ==============

curl https://registry.npmjs.com/-/all | sync-npm serialize | sync-npm upsert
