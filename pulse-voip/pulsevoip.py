# -*- coding: utf-8 -*-
import sys
import logging
import subprocess
import re
import time
import socket
import os.path
import readline
import colorama

colorama.init(autoreset=True)

logger = logging.getLogger('PulseVoIP')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(colorama.Fore.WHITE + colorama.Style.DIM + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + colorama.Style.NORMAL + colorama.Fore.RESET))
logger.addHandler(handler)

#def pacmd(command):
#	if type(command) != list:
#		command = [ command ]
#	command = [ 'pacmd' ] + command
#	return subprocess.check_output(command)


def pactl(command, wrapper=None):
	"""
	command: pactl command (should be a list)
	wrapper: wrapper command (e.g. [ 'ssh', 'user@host' ])
	"""
	if type(command) != list:
		command = [ command ]
	command = [ 'pactl' ] + command
	
	if not wrapper is None:
		if type(wrapper) != list:
			wrapper = [ wrapper ]
		
		command = wrapper + command
	
	logger.debug("pactl: %s" % command)
	
	return subprocess.check_output(command)


def text2dict(typeid, text, dictkeys=['Properties']):
	blocks = re.split(typeid + ' #', text)
	blocks = map(lambda x: x.strip(), blocks)
	blocks = filter(lambda x: len(x) > 0, blocks)
	
	outdict = dict()
	for block in blocks:
		block = re.split(r'\n\t', block)
		index = int(block[0])
		block = block[1:]
		
		d = dict()
		key = None
		indent = ''
		for line in block:
			if len(line) > 0 and str.isspace(line[0]):
				if key in dictkeys:
					s = line.strip()
					if len(s) > 0:
						s = s.split('=', 1)
						v = s[1].strip()
						if v[0] == '"' and v[-1] == '"':
							v = v[1:-1]
						d[key][s[0].strip()] = v
				else:
					if len(d[key]) > 0:
						d[key] += '\n'
					d[key] += line.strip()
			
			else:
				line = line.split(':', 1)
				key = line[0].strip()
				
				if key in dictkeys:
					d[key] = dict()
					
					s = line[1].strip()
					if len(s) > 0:
						s = s.split('=', 1)
						d[key][s[0].strip()] = s[1].strip()
					
				else:
					d[key] = line[1].strip()
		
		outdict[index] = d
		
	return outdict


def list_modules(wrapper=None):
	return text2dict("Module", pactl(['list', 'modules'], wrapper=wrapper))
	

def list_sources(wrapper=None):
	return text2dict("Source", pactl(['list', 'sources'], wrapper=wrapper))


def list_sinks(wrapper=None):
	return text2dict("Sink", pactl(['list', 'sinks'], wrapper=wrapper))


def get_stat(wrapper=None):
	return pactl(['stat'], wrapper=wrapper)


def get_default_sink_name(stat=None):
	if stat is None:
		stat = get_stat()
	
	return filter(lambda x: x.startswith('Default Sink: '), stat.split('\n'))[0].split(':', 1)[1].strip()


def get_default_source_name(stat=None):
	if stat is None:
		stat = get_stat()
	
	return filter(lambda x: x.startswith('Default Source: '), stat.split('\n'))[0].split(':', 1)[1].strip()


def get_module_info(name, modules=None, wrapper=None):
	if modules is None:
		modules = list_modules(wrapper=wrapper)
	
	return { k: v for k, v in modules.iteritems() if v['Name'] == name }


def get_sink_info(name, sinks=None, wrapper=None):
	if sinks is None:
		sinks = list_sinks(wrapper=wrapper)
	
	return [ v for k, v in sinks.iteritems() if v['Name'] == name ][0]


def get_source_info(name, sources=None, wrapper=None):
	if sources is None:
		sources = list_sources(wrapper=wrapper)
	
	return [ v for k, v in sources.iteritems() if v['Name'] == name ][0]


def unload_module(index, wrapper=None):
	logger.debug("Unloading module #%s" % index)
	try:
		pactl(['unload-module', str(index)], wrapper=wrapper)
	except Exception:
		logger.error('Unloading module #%s failed.' % index)


def unload_modules(name, modules=None, wrapper=[]):
	logger.info("Unloading module %s" % name)
	info = get_module_info(name, modules=modules, wrapper=wrapper)
	for index in info.keys():
		unload_module(index, wrapper=wrapper)


def load_module(name, arguments=[], wrapper=[]):
	logger.info('Loading module %s with arguments %s' % (name, arguments))
	return int(pactl(['load-module', name] + arguments, wrapper).strip())


def get_tunneled_sources(remote_ip=None, sources=None):
	if sources is None:
		sources = list_sources()
	
	tunneled = { k: v for k, v in sources.iteritems() if v['Driver'] == 'module-tunnel.c' }
	if not remote_ip is None:
		tunneled = { k: v for k, v in sources.iteritems() if v['Properties'].get('tunnel.remote.server', '').startswith('[%s]:' % remote_ip) }
	
	return tunneled


def get_tunneled_sinks(remote_ip=None, sinks=None):
	if sinks is None:
		sinks = list_sinks()
	
	tunneled = { k: v for k, v in sinks.iteritems() if v['Driver'] == 'module-tunnel.c' }
	if not remote_ip is None:
		tunneled = { k: v for k, v in sinks.iteritems() if v['Properties'].get('tunnel.remote.server', '').startswith('[%s]:' % remote_ip) }
	
	return tunneled


def add_loopback(source, sink, wrapper=None):
	logger.info('Adding Loopback %s -> %s' % (source, sink))
	return load_module('module-loopback', ['source=' + source, 'sink=' + sink, 'latency_msec=1'], wrapper=wrapper)
	#, 'latency_msec=500'])
	#, 'latency_msec=1', ])


def start_pacat_loopback(source, sink, latency_rec=5, latency_play=5, wrapper=None):
	"""
	Alternative loopback using two pacat processes.
	Has lower latency than module-loopback.
	source/sink are pasted in a shell command!
	"""
	
	logger.info('Starting pacat loopback %s -> %s' % (source, sink))
	
	command = 'pacat -r --latency-msec %d -d %s | pacat -p --latency-msec %d -d %s' % (latency_rec, source, latency_play, sink)
	
	# bash won't react to signals while waiting for child processes
	command = 'trap \'kill $(jobs -p)\' EXIT;' + command
	command += r' & wait %-'
	
	# shell=True might do as well, but...
	command = [ 'bash', '-ec', command ]
	
	if not wrapper is None:
		if type(wrapper) != list:
			wrapper = [ wrapper ]
		
		command = wrapper + command
	
	logger.debug("%s" % command)
	
	process = subprocess.Popen(
		command
		#stdout=subprocess.STDOUT,
		#stderr=subprocess.STDERR
	)
	
	return process


def stop_pacat_loopback(p):
	"""
	p: the output of start_pacat_loopback
	"""

	logger.debug('Sending SIGINT to %d...' % p.pid)
	p.send_signal(subprocess.signal.SIGINT)
	logger.debug('Waiting for process %d...' % p.pid)
	p.wait()
	logger.debug('Process %d exited.' % p.pid)
	

def print_info():
	print "Default local sink:"
	print '•', get_default_sink_name()
	print

	print "Default local source:"
	print '•', get_default_source_name()
	print

	print "Discovered tunneled sinks:"
	a = get_tunneled_sinks()
	for key in a.keys():
		print '•', a[key]['Properties'].get('tunnel.remote.server', '[?]'), a[key]['Name']
	print

	print "Discovered tunneled sources:"
	a = get_tunneled_sources()
	for key in a.keys():
		print '•', a[key]['Properties'].get('tunnel.remote.server', '[?]'), a[key]['Name']
	print


def wait_for_source(name):
	logger.info('Waiting for source %s...' % name)
	while True:
		sources = list_sources()
		filtered = filter(lambda (k,v): v['Name'] == name, sources.iteritems())
		if len(filtered) > 0:
			return filtered[0]
		
		time.sleep(1)
		logger.debug('Still waiting for source %s...' % name)


def wait_for_sink(name):
	logger.info('Waiting for sink %s...' % name)
	while True:
		sinks = list_sinks()
		filtered = filter(lambda (k,v): v['Name'] == name, sinks.iteritems())
		if len(filtered) > 0:
			return filtered[0]
		
		time.sleep(1)
		logger.debug('Still waiting for sink %s...' % name)


def get_local_address():
	"""
	Returns the address used to construct tunnel device names.
	"""
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect(("www.lsv.uni-saarland.de", 80))
		return s.getsockname()[0]
	finally:
		s.close()


def get_tunnel_hostname():
	# socket.getfqdn() seems to be wrong
	fqdn = socket.gethostname()
	if not '.' in fqdn:
		fqdn = fqdn + '.local'
	return fqdn


def init_readline(commands):
	readline.parse_and_bind("tab: complete")
	
	def complete(text, state):
		possibilities = [ x for x in commands if x.startswith(text) ] + [ None ]
		return possibilities[state]

	readline.set_completer(complete)


ZEROCONF_TYPE_PA_SINK = '_pulse-sink._tcp'
ZEROCONF_TYPE_PA_SOURCE = '_pulse-source._tcp'
ZEROCONF_TYPE_PA_SERVER = '_pulse-server._tcp'


def avahi_browse(zeroconf_type, ipversion='IPv4', address=None, device=None, wait=0, hidelocal=True):
	command = [ 'avahi-browse', '-cpkr', zeroconf_type ]
	while True:
		l = subprocess.check_output(command).strip().split('\n')
		
		# avahi-browse -p has a rather unusual idea of escaping strings.
		# \064 for example is actually 64 decimal.
		# meow.
		l = map(lambda x: map(lambda y: re.sub(r'\\[0-9][0-9][0-9]', lambda z: chr(int(z.group()[1:4])), y), x.split(';')), l)
		l = filter(lambda x: x[0] == '=' and x[2] == ipversion, l)
		
		if not address is None:
			l = filter(lambda x: x[7] == address, l)
		
		local_address = get_local_address()
		if hidelocal:
			l = filter(lambda x: x[7] != local_address, l)
		
		def l2d(l):
			return {
				'c' : l[0],
				'interface' : l[1],
				'protocol' : l[2],
				'service_name' : l[3],
				'type': l[4],
				'domain': l[5],
				'host_name' : l[6],
				'address' : l[7],
				'port' : int(l[8]),
				# avahi_string_list_to_string does not escape quotation marks?
				'properties' : dict(map(lambda x: x.split('=', 1), l[9][1:-1].split('" "')))
			}
			
		l = map(l2d, l)
		
		if not device is None:
			l = filter(lambda x: x['properties']['device'] == device, l)
		
		if len(l) == 0 and wait > 0:
			time.sleep(1)
			continue
		
		return l


def select_avahi_device(devtype, address=None, hidelocal=True):
	if devtype == 'source':
		zeroconf_type = ZEROCONF_TYPE_PA_SOURCE
	elif devtype == 'sink':
		zeroconf_type = ZEROCONF_TYPE_PA_SINK
	else:
		raise Exception('Unsupported device type: %s' % devtype)
	
	while True:
		discovered = avahi_browse(zeroconf_type, address=address, hidelocal=hidelocal)
		
		print
		print colorama.Fore.WHITE + colorama.Style.BRIGHT + 'Discovered %ss:' % devtype
		i = 0
		for dev in discovered:
			print '[%s%d%s] %s (%s)' % (
				colorama.Fore.GREEN + colorama.Style.BRIGHT,
				i,
				colorama.Style.NORMAL + colorama.Fore.RESET,
				dev['service_name'], dev['properties']['device']
			)
			i += 1
			
		if i == 0:
			print '(None)'
			print
		
		if len(discovered) == 0:
			s = raw_input('No remote devices found. Make sure the client is running on the remote computer and hit Enter to rescan: ').strip()
		else:
			s = raw_input('Type a device number, or just hit Enter to rescan: ').strip()
		if len(s) == 0:
			continue
		try:
			n = int(s)
		except ValueError:
			continue
			
		if n >= 0 and n < len(discovered):
			return discovered[n]


def tunnel_args_from_avahi(info):
	if info['type'] == ZEROCONF_TYPE_PA_SOURCE:
		devtype = 'source'
	elif info['type'] == ZEROCONF_TYPE_PA_SINK:
		devtype = 'sink'
	else:
		raise Exception('Unsupported zeroconf type: %s' % info['type'])
	
	return (
		'module-tunnel-%s' % devtype,
		[
			'server=[%s]:%s' % (info['address'], info['port']),
			'%s=%s' % (devtype, info['properties']['device']),
			'format=%s'  % info['properties']['format'],
			'channels=%s' % info['properties']['channels'],
			'rate=%s' % info['properties']['rate'],
			'%s_name=tunnel.%s.%s' % (devtype, info['host_name'], info['properties']['device']),
			'channel_map=%s' % info['properties']['channel_map']
		]
	)


def tunnel_args(
	hostname, port, device, devtype,
	format='s16le', channels=1,
	rate=44100, channelmap='mono',
	address=None
):
	"""
	port: usually 4713
	devtype: source|sink
	"""
	if address is None:
		address = socket.gethostbyname(hostname)
	
	return (
		'module-tunnel-%s' % devtype,
		[
			'server=[%s]:%s' % (address, port),
			'%s=%s' % (devtype, device),
			'format=%s'  % format,
			'channels=%s' % channels,
			'rate=%s' % rate,
			'%s_name=tunnel.%s.%s' % (devtype, hostname, device),
			'channel_map=%s' % channelmap
		]
	)
	
	#['server=[134.96.116.27]:4713', 'source=alsa_input.usb-Sennheiser_Communications_Sennheiser_USB_headset-00-headset.analog-mono', 'format=s16le', 'channels=1', 'rate=44100', 'source_name=tunnel.ws47lx.local.alsa_input.usb-Sennheiser_Communications_Sennheiser_USB_headset-00-headset.analog-mono', 'channel_map=mono']


def create_tunnel(info, wrapper=None):
	"""
	Returns module index and (guessed) local device name.
	"""
	module = load_module(*tunnel_args_from_avahi(info), wrapper=wrapper)
	return (module, 'tunnel.%s.%s' % (info['host_name'], info['properties']['device']))


def create_tunnel_direct(
	hostname, port, device, devtype,
	format='s16le', channels=1,
	rate=44100, channelmap='mono',
	address=None,
	wrapper=None
):
	module = load_module(*tunnel_args(hostname, port, device, devtype, format=format, channels=channels, rate=rate, channelmap=channelmap, address=address), wrapper=wrapper)
	return (module, 'tunnel.%s.%s' % (hostname, device))
