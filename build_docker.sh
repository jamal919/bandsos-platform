#!/bin/bash
# Multiplatform: https://docs.docker.com/build/building/multi-platform/
# docker login
docker login
docker run --privileged --rm tonistiigi/binfmt --install all

# builder
docker buildx create --name mybuilder --driver docker-container --use
docker buildx inspect --bootstrap

# building
GIT_SHA=$(git rev-parse --short HEAD)

docker buildx build --platform linux/amd64 \
      --push \
      -t jamal919/bandsos:$GIT_SHA \
      -t jamal919/bandsos:latest \
      -f Dockerfile .

docker pull jamal919/bandsos:latest
