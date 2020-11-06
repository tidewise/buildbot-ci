ARG buildbot_base=buildbot/buildbot-worker

FROM $buildbot_base

USER root

RUN ( curl -sL https://deb.nodesource.com/setup_12.x | bash - )
RUN apt-get update && \
    apt-get install -y sudo ruby ruby-dev wget curl build-essential nodejs && \
    npm install -g xunit-viewer && \
    rm -rf /var/lib/apt/lists/*

COPY files/etc/sudoers.d/buildbot /etc/sudoers.d/
COPY files/etc/apt/apt.conf.d/01disable_suggests_recommends /etc/apt/apt.conf.d/01disable_suggests_recommends

RUN mkdir -p /var/cache/autoproj/import && \
    mkdir -p /var/cache/autoproj/build && \
    chown -R buildbot /var/cache/autoproj && \
    chmod -R go+rx /var/cache/autoproj
COPY files/etc/apt/apt.conf.d/01cache /etc/apt/apt.conf.d/01cache

COPY --chown=buildbot files/home/.bundle/config /home/buildbot/.bundle/config

USER buildbot
