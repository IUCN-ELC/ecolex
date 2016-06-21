#!/bin/sh

export SOLR_URI=http://solr:8983/solr/ecolex

/bin/date >> /ecolex/crontab.log
echo "Started treaty importer from cron" >> /ecolex/crontab.log
/usr/local/bin/python /ecolex/manage.py import treaty
echo "Treaty importer from cron finished" >> /ecolex/crontab.log
/bin/date >> /ecolex/crontab.log
echo "Started treaty importer (status update) from cron" >> /ecolex/crontab.log
/usr/local/bin/python /ecolex/manage.py import treaty --update-status
echo "Treaty importer (status update) from cron finished" >> /ecolex/crontab.log

/bin/date >> /ecolex/crontab.log
echo "Started literature importer from cron" >> /ecolex/crontab.log
/usr/local/bin/python /ecolex/manage.py import literature
echo "Literature importer from cron finished" >> /ecolex/crontab.log

/bin/date >> /ecolex/crontab.log
echo "Started decision importer from cron" >> /ecolex/crontab.log
/usr/local/bin/python /ecolex/manage.py import decision
echo "Decision importer from cron finished" >> /ecolex/crontab.log

/bin/date >> /ecolex/crontab.log
echo "Started court decision importer from cron" >> /ecolex/crontab.log
/usr/local/bin/python /ecolex/manage.py import court_decision
echo "Court decision importer from cron finished" >> /ecolex/crontab.log
/bin/date >> /ecolex/crontab.log
