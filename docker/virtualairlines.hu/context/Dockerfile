FROM ubuntu:18.04

RUN apt-get update -y && \
    /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    software-properties-common && \
    add-apt-repository -y ppa:ondrej/php && \
    apt-get update -y && \
    /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    patch \
    mysql-client \
    mysql-server \
    apache2 \
    php5.6 \
    php5.6-mysql \
    php5.6-xml && \
    apt-get clean -y

COPY entrypoint.sh init.sql php.ini.patch /

ENTRYPOINT ["/entrypoint.sh"]
CMD ["mava"]
