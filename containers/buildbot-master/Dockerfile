ARG buildbot_base=buildbot/buildbot-master
FROM $buildbot_base

RUN apk add cairo libjpeg-turbo libgcc 

RUN apk add zlib-dev libjpeg-turbo-dev python3-dev build-base && \
    pip3 --no-cache-dir install 'txrequests' buildbot-badges flask \
        buildbot-wsgi_dashboards && \
    apk del zlib-dev libjpeg-turbo-dev python3-dev build-base

RUN apk add py3-libvirt

COPY 'configure-host-and-exec' '/usr/local/bin'

CMD ["/usr/local/bin/configure-host-and-exec", "dumb-init", "/usr/src/buildbot/docker/start_buildbot.sh"]
