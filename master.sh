#! /bin/sh

PROJECT_NAME=$1
if test -z "$PROJECT_NAME"; then
    echo "Usage: master.sh PROJECT_NAME"
    exit 1
fi

docker run -p 9989:9989 -p 8666:8666 \
    --mount type=bind,src=$PWD,dst=/var/lib/buildbot \
    gcr.io/$1/buildbot-master
