#!/usr/bin/env bash

# Exit if any subcommands or pipeline returns a non-zero status.
set -e

# Make a database for Gratipay.
#
#   usage: DATABASE_URL=postgres://foo:bar@baz:5234/buz recreate-schema.sh

echo "=============================================================================="

# I got the idea for dropping the schema as a way to clear out the db from
# http://www.postgresql.org/message-id/200408241254.19075.josh@agliodbs.com. On
# Heroku Postgres we don't have permission to drop and create the db as a
# whole.

echo "Recreating public schema ... "
echo "DROP SCHEMA public CASCADE" | psql "$DATABASE_URL"
echo "CREATE SCHEMA public" | psql "$DATABASE_URL"


echo "=============================================================================="
echo "Enforcing UTC ..."
echo

psql "$DATABASE_URL" < sql/enforce-utc.sql


echo "=============================================================================="
echo "Applying sql/schema.sql ..."
echo

psql "$DATABASE_URL" < sql/schema.sql


echo "=============================================================================="
echo "Loading sql/countries.sql ..."
echo

psql "$DATABASE_URL" < sql/countries.sql


echo "=============================================================================="
echo "Applying deploy hooks ..."
echo

cd deploy 
if [ -e before.sql -o -e after.py -o -e after.sql ]
then
    [ -e before.sql ] && echo 'Found before.sql ...' && psql "$DATABASE_URL" < before.sql 
    [ -e after.py ] && echo 'Found after.py ...' && env/bin/python after.py
    [ -e after.sql ] && echo 'Found after.sql ...' && psql "$DATABASE_URL" < after.sql
else
    echo "None found. That's cool. See deploy/README.md if you want to modify the "
    echo "database as part of your pull request."
fi
cd ..
echo


echo "=============================================================================="
echo
echo "Okay! Initialized \"$DATABASE_URL\"."
echo
echo "=============================================================================="
