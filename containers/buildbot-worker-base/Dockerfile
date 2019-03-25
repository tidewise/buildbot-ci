FROM        ubuntu:18.04
MAINTAINER  TideWise

ARG WORKER_SRCDIR

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ENV         security_updates_as_of 2018-06-15

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

# Install security updates and required packages
RUN         apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install -q \
    build-essential \
    git \
    subversion \
    python3-dev \
    libffi-dev \
    libssl-dev \
    python3-setuptools \
    python3-pip \
    curl && \
    rm -rf /var/lib/apt/lists/* && \
    # Test runs produce a great quantity of dead grandchild processes.  In a
    # non-docker environment, these are automatically reaped by init (process 1),
    # so we need to simulate that here.  See https://github.com/Yelp/dumb-init
    curl https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64.deb -Lo /tmp/init.deb && dpkg -i /tmp/init.deb &&\
    # Install required python packages, and twisted
    pip3 --no-cache-dir install 'twisted[tls]' && \
    mkdir /buildbot &&\
    useradd -ms /bin/bash buildbot

COPY buildbot/worker /usr/src/buildbot-worker
COPY buildbot/worker/docker/buildbot.tac /buildbot/buildbot.tac

RUN pip3 install /usr/src/buildbot-worker && \
    chown -R buildbot /buildbot

USER buildbot
WORKDIR /buildbot

CMD ["/usr/bin/dumb-init", "twistd", "--pidfile=", "-ny", "buildbot.tac"]
