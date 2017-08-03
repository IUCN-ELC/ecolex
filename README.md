Ecolex.org
================

[![Docker Automated build](https://img.shields.io/docker/automated/iucn/ecolex_web.svg)](https://hub.docker.com/u/iucn/)

## Project Name

The Project Name is ECOLEX.

### Requirements

1. one or multiple servers running your choice of Linux flavor (the steps below were tested on CentOS Linux 7).
2. JRE (at least 1.7) on each node.

### Installation

#### Install using Docker
 
In order to install the project for development, you have to clone this repo, gain access to the [ecolex.docker](https://gitlab.com/ecolex/ecolex.docker) gitlab repo and follow the instruction from there.

The project uses 3 docker images ( web, maria and solr) and a docker-compose file located in the gitlab repo.

The images are build and pushed automatically in the following dockerhub repos: [web](https://hub.docker.com/r/iucn/ecolex_web/), [maria](https://hub.docker.com/r/iucn/ecolex_maria/) and [solr](https://hub.docker.com/r/iucn/ecolex_solr/) .

All 3 images are rebuild on every push on the master branch of this repo.
 
 
##### Web image
The image is build using [this](/Dockerfile) Dockerfile. In the [web](/docker/web) directory you can find two sh files(`root-entrypoint.sh` and `entrypoint.sh`) used as entrypoints for docker image, `ecolex.crontab` file containing cron tasks and files used for those tasks (`import_updater.sh`, `reprocess_from_db.sh`) .
 
##### Ecolex Maria image
The image is build from [this](/docker/maria) folder. It contains a [Dockerfile](/docker/maria/Dockerfile) and an entrypoint.
 
##### Ecolex Solr image
The image is build from [this](/docker/solr) folder. It contains a [Dockerfile](/docker/solr/Dockerfile), .sh files and the xml schema which is copied inside the image.

#### Install without Docker
Download and install (as superuser) solr inside `/var/local/solr-x.y.z`:

	$ cd /var/local
	$ wget http://mirrors.hostingromania.ro/apache.org/lucene/solr/4.10.3/solr-4.10.3.tgz
	$ cd solr-4.10.3/example
	$ ls webapps/

There should be a `solr.war` file inside the webapps folder.

Configure a new collection starting from collection1:

	$ cp -r solr/collection1 solr/ecolex_conf

Replace the collection's schema with the one from the repo:

	$ cp /var/local/ecolex-prototype/configs/schema.xml solr/ecolex_conf/conf/

Start SOLR (by default it uses the port 8983):

	$ java -DzkHost=localhost:2181 -jar start.jar

ZK will run just on one node, so when installing SOLR on other nodes, use the LAN_IP to connect to ZK.

	$ java -DzkHost=10.0.0.98:2181 -jar start.jar

You can now check the admin page on any of the SOLR nodes:

	http://127.0.0.1:8983/solr/admin/

If you modified the schema.xml or the solrconfig.xml and want to update it, use the "Core Admin" panel from
the Solr dashboard (http://127.0.0.1:8983/solr/#/~cores/) . Press the reload button and configuration files will update.


## Django application

We are using Python 3 for the web server application. Initialize an environment with:

    $ pyvenv sandbox
    $ source sanbox/bin/activate
    $ pip install -r requirements.txt
    $ ./manage.py treaties_cache

Run with:

    $ ./manage.py runserver

### Configuration settings

Create a file `local_settings.py` in the same path as `manage.py`. There are two axamples of local_settings file inside
the ecolex directory: one is used for initial data import (which will import all data), and the other one for the data
updates (queryes the new records for the previous month).

To enable spelling suggestions, set:

    TEXT_SUGGESTION = True


If you wish to attach the rich text content when adding the treaties, start a tika server locally and set TEXT_UPLOAD_ENABLED in import_elis.py (you can configure the tika connection details in contrib/utils.py).

## Cron job for document updates:
	The Dockerfile has rules for installing cron in container, and it imports the crontab.example
	into it. If the cron is not running check with `crontab -l` that there is a newline at the end
	of the file. If still not working try to restart the cron service with `/etc/init.d/cron restart` command runned inside the container.

