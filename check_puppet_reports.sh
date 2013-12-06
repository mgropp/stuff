#!/bin/bash
set -e
set -u

STATE_OK=0
STATE_WARNING=1
STATE_CRITICAL=2
STATE_UNKNOWN=3
STATE_DEPENDENT=4

logfile=/var/log/check-puppet-reports.log
if [ ! -r "$logfile" ]
then
	echo "Log file not readable!"
	exit $STATE_CRITICAL
fi

status=$( tail -n1 "$logfile" )
echo "Puppet reports: $status"
if ( echo "$status" | egrep -q '^OK' )
then
	exit $STATE_OK
elif ( echo "$status" | egrep -q '^ALARM' )
then
	exit $STATE_CRITICAL
else
	exit $STATE_WARNING
fi
