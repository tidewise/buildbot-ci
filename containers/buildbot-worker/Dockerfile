ARG buildbot_worker_base
FROM $buildbot_worker_base

USER root

RUN apt-get update && \
    apt-get install -y sudo ruby ruby-dev wget build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY files/etc/sudoers.d/buildbot /etc/sudoers.d/
COPY files/etc/apt/apt.conf.d/01disable_suggests_recommends /etc/apt/apt.conf.d/01disable_suggests_recommends

COPY cleanup-qtbindings.sh /tmp/cleanup-qtbindings.sh
RUN sudo apt-get update && \
    sudo apt-get install -y cmake libqt4-dev libx11-dev libgl1-mesa-dev libqt4-opengl-dev && \
    su - buildbot sh -c "GEM_HOME=/home/buildbot/.local/share/autoproj/gems/ruby/2.5.0 gem install --no-document qtbindings" && \
    sh /tmp/cleanup-qtbindings.sh && \
    apt-get remove --purge -y cmake libqt4-dev libx11-dev libgl1-mesa-dev libqt4-opengl-dev && \
    apt-get autoremove --purge -y && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /tmp/cleanup-qtbindings.sh

ARG XVIEWER_VERSION=6.0.10

RUN apt-get update && \
    apt-get install -y nodejs npm && \
    npm install -g xunit-viewer && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/cache/autoproj/import && \
    mkdir -p /var/cache/autoproj/build && \
    chmod -R go+rx /var/cache/autoproj
COPY files/etc/apt/apt.conf.d/01cache /etc/apt/apt.conf.d/01cache

COPY --chown=buildbot files/home/.bundle/config /home/buildbot/.bundle/config

USER buildbot
