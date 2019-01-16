FROM ubuntu:cosmic

RUN dpkg --add-architecture i386 && \
    apt-get update -y && \
    /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y \
        tzdata \
        wget \
        wine \
        wine32 && \
    echo "Europe/Budapest" > /etc/timezone && \
    rm -f /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

ADD entrypoint.sh setup.sh build.sh /root/

ENTRYPOINT ["/root/entrypoint.sh"]
CMD ["bash"]
