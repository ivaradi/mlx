FROM ubuntu:focal-20200423

RUN apt-get update -y && \
    /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    software-properties-common && \
    add-apt-repository -y ppa:ondrej/php && \
    apt-get update -y && \
    /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    patch \
    mysql-client \
    mysql-server \
    apache2 \
    php5.6 \
    php5.6-mysql \
    php5.6-xml && \
    apt-get clean -y

COPY entrypoint.sh init.sql php.ini.patch /
COPY mysql.cnf /etc/mysql/conf.d

ENTRYPOINT ["/entrypoint.sh"]
CMD ["mava"]
