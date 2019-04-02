FROM buildbot/buildbot-master:master

RUN apk add cairo libjpeg-turbo libgcc 

RUN apk add zlib-dev libjpeg-turbo-dev python3-dev build-base && \
    pip3 --no-cache-dir install 'txrequests' buildbot-badges flask \
        buildbot-wsgi_dashboards && \
    apk del zlib-dev libjpeg-turbo-dev python3-dev build-base
