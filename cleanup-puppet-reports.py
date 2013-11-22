#!/usr/bin/env python3
from glob import glob, iglob
import os
import os.path
from datetime import datetime, timedelta

basedir = '/var/lib/puppet/reports'
max_age = timedelta(weeks=2)


def get_age(filename):
	try:
		(_, filename) = os.path.split(filename)
		if len(filename) != 17:
			return None
		if filename[12:17] != '.yaml':
			return None

		return datetime.utcnow() - datetime.strptime(filename[0:12], '%Y%m%d%H%M')
	
	except Exception:
		return None


deleted = 0
kept = 0
for dir in iglob(os.path.join(basedir, '*')):
	if not os.path.isdir(dir):
		print('%s is not a directory' % dir)
		continue
	
	files = glob(os.path.join(dir, '*.yaml'))
	files.sort()

	# never delete the latest report
	files.pop()

	for filename in files:
		age = get_age(filename)
		if age is None or age <= max_age:
			print('keep %s (age %s)' % (filename, age))
			kept += 1
		else:
			print('delete %s (age %s)' % (filename, age))
			os.unlink(filename)
			deleted += 1
		
print()
print('Deleted %d files, kept %d files.' % (deleted, kept))
