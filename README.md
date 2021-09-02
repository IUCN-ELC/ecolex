Ecolex.org
================

[![Docker build](https://img.shields.io/docker/build/iucn/ecolex_web.svg)](https://hub.docker.com/r/iucn/ecolex_web/builds) [![Updates](https://pyup.io/repos/github/IUCN-ELC/ecolex/shield.svg)](https://pyup.io/repos/github/IUCN-ELC/ecolex/)


#### Install using Docker
 
In order to install the project for development, you have to clone this repo, gain access to the [ecolex.docker](https://github.com/IUCN-ELC/ecolex.docker) github repo and follow the instruction from there.

The project uses 3 docker images ( web, maria and solr) and a docker-compose file is located in the [ecx](https://github.com/IUCN-ELC/ecolex.docker/tree/master/ecx) directory of `ecolex.docker`.

~~The web image is build and pushed automatically in the following dockerhub repo: [web](https://hub.docker.com/r/iucn/ecolex_web/). The image is rebuild on every push on the master branch of this repo.~~

The `web` image is build using [this](/Dockerfile) Dockerfile. In the [docker](/docker) directory you can find a sh file(`docker-entrypoint.sh`) used as entrypoint for docker image, `ecolex.crontab` file containing cron tasks and files used for those tasks (`import_updater.sh`, `reprocess_from_db.sh`) .
 
## Django application

We are using Python 3 for the web server application. Initialize an environment with:

    $ pyvenv sandbox
    $ source sanbox/bin/activate
    $ pip install -r requirements.txt

Run with:

    $ ./manage.py runserver

