#!/usr/bin/env bash


# Fail on error
set -e


# Be somewhere predictable
cd "$(dirname "$0")"


# Helpers

yesno () {
    proceed=""
    while [ "$proceed" != "y" ]; do
        read -p"$1 (y/n) " proceed
        [ "$proceed" = "n" ] && return 1
    done
    return 0
}

require () {
    if [ ! "$(which "$1")" ]; then
        echo "The '$1' command was not found."
        exit 1
    fi
}

maybe_commit () {
    if git commit --dry-run &> /dev/null; then git commit -m "$1"; fi
}


# Check that we have the required tools
require heroku
require git
require curl
require pg_dump


# Make sure we have the latest master
if [ "$(git rev-parse --abbrev-ref HEAD)" != "master" ]; then
    echo "Not on master, checkout master first."
    exit
fi
git pull


# Compute the next version number
prev="$(git describe --tags --match '[0-9]*' | cut -d- -f1 | sed 's/\.//g')"
version="$((prev + 1))"


# Check that the environment contains all required variables
heroku config -s -a gratipay | ./env/bin/honcho run -e /dev/stdin \
    ./env/bin/python -m gratipay.wireup


# Sync the translations
echo "Syncing translations ..."
if [ ! -e .transifexrc ] && [ ! -e ~/.transifexrc ]; then
    heroku config -s -a gratipay | ./env/bin/honcho run -e /dev/stdin make transifexrc
fi
make i18n_upload
make i18n_download
git add i18n
maybe_commit("Update i18n files")


# Ask confirmation and bump the version
yesno "Tag and deploy version $version?" || exit
echo $version > www/version.txt
git commit www/version.txt -m "Bump version to $version"
git tag $version


# Deploy to Heroku, with hooks
cd deploy
[ -e before.sql ] && heroku pg:psql -a gratipay < before.sql
git push --force heroku master
[ -e after.py ] && heroku run -a gratipay python deploy/after.py
[ -e after.sql ] && heroku pg:psql -a gratipay < after.sql
cd ..


# Clear deploy hooks and dump production schema back to schema.sql
rm -rf deploy/{before,after}.{sql,py} deploy/test*
pg_dump --schema-only \
        --no-owner \
        --no-privileges \
        "`heroku config:get DATABASE_URL -a gratipay`" \
        > sql/schema.sql
git add deploy sql/schema.sql
maybe_commit("Clear deploy hooks and update schema.sql")


# Push to GitHub
git push
git push --tags


# Provide visual confirmation of deployment.
echo "Checking version.txt ..."
curl https://gratipay.com/version.txt
