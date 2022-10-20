docker login
docker run --privileged --rm docker/binfmt:a7996909642ee92942dcd6cff44b9b95f08dad64
docker buildx build --platform linux/amd64 --push -t jamal919/bandsos:latest .
docker buildx build --load -t jamal919/bandsos:latest .