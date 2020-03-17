ARG buildbot_worker_base

FROM ubuntu:18.04 AS xviewer-install
USER root

ARG XVIEWER_VERSION=6.0.10

RUN apt-get update && \
    apt-get install -y nodejs npm && \
    npm install -g xunit-viewer && \
    rm -rf /var/lib/apt/lists/*

FROM $buildbot_worker_base

USER root

RUN apt-get update && \
    apt-get install -y sudo ruby ruby-dev wget build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY files/etc/sudoers.d/buildbot /etc/sudoers.d/
COPY files/etc/apt/apt.conf.d/01disable_suggests_recommends /etc/apt/apt.conf.d/01disable_suggests_recommends
COPY --from=xviewer-install /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=xviewer-install /usr/local/bin /usr/local/bin

RUN apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/cache/autoproj/import && \
    mkdir -p /var/cache/autoproj/build && \
    chmod -R go+rx /var/cache/autoproj
COPY files/etc/apt/apt.conf.d/01cache /etc/apt/apt.conf.d/01cache

COPY --chown=buildbot files/home/.bundle/config /home/buildbot/.bundle/config
ENV LD_LIBRARY_PATH=/home/buildbot/.local/share/autoproj/gems/ruby/2.5.0/gems/qtbindings-4.8.6.5-x86_64-linux/lib/2.5

USER buildbot
