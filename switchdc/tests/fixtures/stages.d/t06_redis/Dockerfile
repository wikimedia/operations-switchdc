FROM docker-registry.wikimedia.org/wikimedia-jessie

RUN apt-get update && apt-get -y install redis-server

ENTRYPOINT '/usr/bin/redis-server'
