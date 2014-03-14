#!/usr/bin/env bash

set -e

# Set login directory to root vagrant share
echo "cd /vagrant" > /etc/profile.d/login-directory.sh

# TODO: Pin apt-get packages to the same versions Heroku uses

# First run only
if [ ! -f /home/vagrant/.created_db ]; then
    echo "Configuring PostgreSQL..."
    sudo -iu postgres bash <<EOF
        psql \
            --quiet \
            --file=/vagrant/${PROJECT_DIRECTORY}/create_db.sql
EOF
    touch /home/vagrant/.created_db
fi

cd /vagrant

# Warn if Windows newlines are detected and try to fix the problem
if grep --quiet --binary --binary-files=without-match $(printf '\r') README.md; then
    echo
    cat development/scripts/crlf-warning.txt
    echo

    echo 'Running "git config core.autocrlf false"'
    git config core.autocrlf false

    exit 1
fi


# Set up the environment, the database, and run Gittip
make env
sudo -u postgres make schema data

# Output helper text
cat <<EOF

Gittip installed! To run,
$ vagrant ssH -c "sudo -iu postgres make run"
EOF
