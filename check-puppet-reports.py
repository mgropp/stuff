#!/usr/bin/env python3
from glob import iglob, glob
import os
import os.path
import yaml
from datetime import datetime, timedelta

max_age = timedelta(days=10)
report_dir = '/var/lib/puppet/reports'

def construct_ruby_object(loader, suffix, node):
	return loader.construct_yaml_map(node)

def construct_ruby_sym(loader, node):
	return loader.construct_yaml_str(node)

yaml.add_multi_constructor("!ruby/object:", construct_ruby_object)
yaml.add_constructor("!ruby/sym", construct_ruby_sym)


def get_report_info(filename):
	"""
	return: (time, status)
	
	status can be:
	failed, changed, unchanged, ...?
	"""
	with open(filename) as f:
		report = yaml.load(f)

	return (report['time'], report['status'])


def check_report(filename):
	"""
	return: (time, age_ok, status)
	"""

	(time, status) = get_report_info(filename)
	# unlike the file name, time is in local time
	return (time, datetime.now() - time <= max_age, status)


count_machines = 0
count_bad_age = 0
count_bad_status = 0

dirs = glob(os.path.join(report_dir, '*'))
dirs.sort()
for dir in dirs:
	if not os.path.isdir(dir):
		print('%s is not a directory' % dir)
		continue

	count_machines += 1	
	machine = os.path.basename(dir)
	if '.' in machine:
		machine = machine[0:machine.find('.')]

	files = glob(os.path.join(dir, '????????????.yaml'))
	if len(files) == 0:
		print('BAD %s: no reports found!' % machine)
		count_bad_age += 1
		continue

	files.sort()
	latest = files[-1]

	(time, age_ok, status) = check_report(latest)
	print('%s %s: %s at %s (age: %s)' % ('OK ' if age_ok and (status != 'failed') else 'BAD' , machine, status, time, 'good' if age_ok else 'bad'))
	if not age_ok:
		count_bad_age += 1
	if (status != 'changed') and (status != 'unchanged'):
		count_bad_status += 1


if count_bad_age == 0 and count_bad_status == 0:
	print('OK (last run: %s, %d computers)' % (datetime.now(), count_machines))
else:
	print('Problems! Age: bad on %d/%d machines. Status: bad on %d/%d machines.' % (count_bad_age, count_machines, count_bad_status, count_machines))
