#!/bin/bash

if test "$1" = "mava"; then
    if test ! -f /root/initialized; then
        echo "Initial run, setting up some directories and symlinks"
        if test ! -d /var/run/apache2; then
            mkdir /var/run/apache2
        fi

        if test ! -d /var/run/mysqld; then
            install -m 755 -o mysql -g root -d /var/run/mysqld
        fi

        mv /var/www/html /var/www/html.orig
        ln -s /data/public_html/www /var/www/html

        mkdir -p /home/ftp/virtualmalev
        ln -s /data/public_html /home/ftp/virtualmalev/public_html

        mkdir -p /home/mavasyst/public_html
        ln -s /data/public_html /home/mavasyst/public_html/mava_old

        cd /etc/php/5.6/apache2
        patch -p0 < /php.ini.patch
    fi

    echo "Starting MySQL"
    su - mysql -s /bin/sh -c "/usr/bin/mysqld_safe" &

    if test ! -f /root/initialized; then
        echo "Sleeping to let MySQL start up properly"
        sleep 5

        echo "Loading database into MySQL"
        cat /init.sql | mysql
        cat /data/uvirtualmalev.sql | mysql mavasyst_mavaold

        touch /root/initialized
    fi

    source /etc/apache2/envvars
    exec apache2 -DFOREGROUND
else
    exec "$@"
fi
