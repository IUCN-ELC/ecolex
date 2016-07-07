Ecolex Prototype
================

## Project Name

The Project Name is Ecolex Prototype.

## SOLRCloud

### Requirements

1. one or multiple servers running your choice of Linux flavor (the steps below were tested on CentOS Linux 7).
2. JRE (at least 1.7) on each node.

### Installation

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

