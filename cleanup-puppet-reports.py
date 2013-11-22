#!/usr/bin/env python3
from glob import glob, iglob
import os
import os.path
from datetime import datetime, timedelta

basedir = os.sep + os.path.join('var', 'lib', 'puppet', 'reports')
max_age = timedelta(days=1)


def get_age(filename):
	(_, filename) = os.path.split(filename)
	if len(filename) != 17:
		return None
	if filename[12:17] != '.yaml':
		return None

	return datetime.now() - datetime.strptime(filename[0:12], '%Y%m%d%H%M')


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
		if get_age(filename) > max_age:
			print('delete ' + filename)
			os.unlink(filename)
			deleted += 1
		else:
			print('keep ' + filename)
			kept += 1

print()
print('Deleted %d files, kept %d files.' % (deleted, kept))
