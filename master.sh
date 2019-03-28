#! /bin/sh

docker run -p 9989:9989 -p 8666:8666 \
    --mount type=bind,src=$PWD,dst=/var/lib/buildbot \
    rockcore/buildbot-master
