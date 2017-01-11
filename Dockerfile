# Dockerfile to build and run Gratipay
# Version 0.2 (March 10, 2015)

################################################## General Information ##################################################

FROM ubuntu:14.04
MAINTAINER Mihir Singh (@citruspi)

ENV DEBIAN_FRONTEND noninteractive

################################################## Install Dependencies #################################################

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main" > /etc/apt/sources.list.d/pgdg.list

RUN gpg --keyserver keys.gnupg.net --recv-key 7FCC7D46ACCC4CF8 && \
    gpg -a --export 7FCC7D46ACCC4CF8 | apt-key add -

RUN apt-get -y update && \
    apt-get -y --no-install-recommends --no-install-suggests install \
                git \
                gcc \
                make \
                g++ \
                libpq-dev \
                libffi-dev \
                libssl-dev \
                python-dev \
                python-pip \
                postgresql-9.3 \
                postgresql-contrib-9.3 \
                language-pack-en && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

################################################## Configure Postgres #################################################

RUN /etc/init.d/postgresql start && su postgres -c "createuser --superuser root" && su postgres -c "createdb gratipay"

################################################# Copy files + Setup Gratipay ##########################################

COPY ./ /srv/gratipay.com/
WORKDIR /srv/gratipay.com
RUN make -j$(nproc) env && /etc/init.d/postgresql start && make -j$(nproc) schema && make -j$(nproc) schema data

################################################ Create a Launch Script ###############################################

RUN echo "#!/bin/bash" >> /usr/bin/gratipay && \
    echo "/etc/init.d/postgresql start" >> /usr/bin/gratipay && \
    echo "cd /srv/gratipay.com && make run" >> /usr/bin/gratipay && \
    chmod +x /usr/bin/gratipay

################################################### Launch command #####################################################

CMD ["/usr/bin/gratipay"]
