#! /bin/sh -e
# Script that creates the container images we need in the cluster, apart
# from the worker itself

project=$1
if test -z "$1"; then
    echo "usage: containers.sh PROJECT"
    exit 1
fi

echo "Setting up for project ${project}"

docker build -t gcr.io/$project/cache-apt containers/apt-cacher-ng
docker build -t gcr.io/$project/cache-gem containers/gemstash
docker pull rockcore/buildbot-worker-base
docker build -t gcr.io/$project/buildbot-worker containers/buildbot-worker

docker push gcr.io/$project/cache-apt
docker push gcr.io/$project/cache-gem
docker push gcr.io/$project/buildbot-worker
