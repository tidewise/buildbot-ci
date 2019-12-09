#! /bin/sh

project_name=$1
container_tag=$2
if test -z "$project_name" || test -z "$container_tag"; then
    echo "Usage: master.sh PROJECT_NAME CONTAINER_TAG"
    exit 1
fi

docker run -p 9989:9989 -p 8666:8666 \
    --mount type=bind,src=$PWD,dst=/var/lib/buildbot \
    gcr.io/$project_name/buildbot-master:$container_tag
