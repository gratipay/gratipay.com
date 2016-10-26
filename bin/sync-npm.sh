#!/bin/sh

set -e
cd "`dirname $0`/.."

# Install dependencies.
pip install -e .
pip install -i ijson==2.3.0
git clone https://github.com/lloyd/yajl.git
cd yajl
git checkout 2.1.0
./configure
sudo make install
cd ..

URL=https://registry.npmjs.com/-/all
URL=https://gist.githubusercontent.com/whit537/fec53fb1f0618b3d5757f0ab687b7476/raw/25de82f6197df49b47d180db0d62b4e8c6f7f9f8/one

curl $URL | sync-npm serialize /dev/stdin | sync-npm upsert /dev/stdin
