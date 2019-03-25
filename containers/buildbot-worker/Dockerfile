FROM rockcore/buildbot-worker-base

USER root

RUN apt-get update && \
    apt-get install -y sudo ruby ruby-dev wget build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY files/etc/sudoers.d/buildbot /etc/sudoers.d/
COPY files/etc/apt/apt.conf.d/01disable_suggests_recommends /etc/apt/apt.conf.d/01disable_suggests_recommends

USER buildbot

RUN sudo apt-get update && \
    sudo apt-get install -y cmake libqt4-dev libx11-dev libgl1-mesa-dev libqt4-opengl-dev && \
    GEM_HOME=/home/buildbot/.local/share/autoproj/gems/ruby/2.5.0 gem install --no-document qtbindings && \
    rm -rf /home/buildbot/.local/share/autoproj/gems/ruby/2.5.0/qtbindings*/ext/build && \
    sudo apt-get remove --purge -y cmake libqt4-dev libx11-dev libgl1-mesa-dev libqt4-opengl-dev && \
    sudo apt-get autoremove --purge -y && \
    sudo rm -rf /var/lib/apt/lists/*

COPY files/home/.bundle/config /home/buildbot/.bundle/config

USER root

COPY files/etc/apt/apt.conf.d/01cache /etc/apt/apt.conf.d/01cache

USER buildbot
