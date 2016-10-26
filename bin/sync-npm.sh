#!/bin/sh

set -e
cd "`dirname $0`/.."

# Install dependencies.
git clone https://github.com/lloyd/yajl.git
cd yajl
git checkout 2.1.0
./configure
sudo make install
cd ..

./env/bin/pip install -i ijson==2.3.0


wget https://registry.npmjs.com/-/all
./env/bin/sync-npm serialize all > serialized
./env/bin/sync-npm upsert serialized
