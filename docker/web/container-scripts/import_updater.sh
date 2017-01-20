#!/usr/bin/env bash

echo `/bin/date` ": Started Treaty importer"
$THIS_HOME/ecolex/manage.py import treaty
echo `/bin/date` ": Finished Treaty importer"

echo `/bin/date` ": Started Treaty importer (status update)"
$THIS_HOME/ecolex/manage.py import treaty --update-status
echo `/bin/date` ": Finished Treaty importer (status update)"

echo `/bin/date` ": Started literature importer"
$THIS_HOME/ecolex/manage.py import literature
echo `/bin/date` ": Finished Literature importer"

echo `/bin/date` ": Started Decision importer"
$THIS_HOME/ecolex/manage.py import decision
echo `/bin/date` ": Finished Decision importer"

echo `/bin/date` ": Started Court decision importer"
$THIS_HOME/ecolex/manage.py import court_decision
echo `/bin/date` ": Finished Court decision importer"
