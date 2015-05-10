#!/bin/sh

set -e # exit when any command fails

echo "[*] Installing base dependencies..
      g++         - for compiling libsass
      git
      libpq-dev   - for compiling psycopg2
      make
      postgresql
      postgresql-contrib  - pg_trgm, pg_stat_statements
      python
      python-dev  - for building misaka"
sudo apt-get update
sudo apt-get install -y \
    g++ \
    git \
    libpq-dev \
    make \
    postgresql \
    postgresql-contrib \
    python \
    language-pack-en \
    python-dev

echo "[*] Installing dependencies for tests..
      default-jre     - jstests need java to run selenium
      nodejs-legacy   - for grunt, which calls 'node' executable,
                        which was renamed to nodejs in Debian/Ubuntu
      npm
"
sudo apt-get install -y \
    default-jre \
    nodejs-legacy \
    npm


echo "[*] Checking if current user has access to create databases.."

if [ -z ""`sudo -i -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$USER'"` ];
then
    echo "'$USER' entry does not exist in PostgreSQL, creating.."
    sudo -i -u postgres createuser --superuser $USER
fi;


echo "[*] Creating databases.."

db_exists() {
    if [ -n ""`psql template1 -tAc "select datname from pg_database where datname='$1'"` ];
    then
        return 0;
    fi
    return 1;
}

if ! db_exists gratipay-test;
then
    echo "..creating gratipay-test"
    createdb gratipay-test
    psql -q gratipay-test -c 'alter database "gratipay-test" set synchronous_commit to off'
fi

if ! db_exists gratipay;
then
    echo "..creating gratipay"
    createdb gratipay
fi

echo "done"
