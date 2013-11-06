import subprocess
import os
import tempfile
import sys
import shutil
import colorama

"""
Use gstreamer to record two PulseAudio streams to a PCM wave file.
"""
class PulseRecorder(object):
	def __init__(self):
		self.process = None
	
	
	def is_recording(self):
		return not self.process is None
	
	
	def record(self, source1, source2, outfile):
		if not self.process is None:
			raise Exception('Already recording!')
		
		self.outfile = outfile
		args = [
			'gst-launch-0.10',
			'interleave', 'name=il', '!',
			'wavenc', '!',
			'filesink', 'location=' + outfile,
			'{',
				'pulsesrc', 'device=' + source1, '!',
				'audioconvert', '!',
				'audio/x-raw-int,width=16,depth=16,endianness=1234,signed=true,channels=1', '!',
				'audioresample', '!',
				'audio/x-raw-int,rate=16000', '!',
				'queue', '!',
				'il.',
			'}',
			'{',
				'pulsesrc', 'device=' + source2, '!',
				'audioconvert', '!',
				'audio/x-raw-int,width=16,depth=16,endianness=1234,signed=true,channels=1', '!',
				'audioresample', '!',
				'audio/x-raw-int,rate=16000', '!',
				'queue', '!',
				'il.',
			'}'
		]
		self.process = subprocess.Popen(args)
		
		#print " ".join(map(lambda x: "'%s'" % x, args))
	
	
	def stop(self, fix_duration=True):
		if self.process is None:
			return
		
		sys.stdout.write(colorama.Fore.WHITE + colorama.Style.DIM)
		try:
			# Don't use .terminate(), apparently gst-launch will not
			# always finish writing its output files that way.
			# -> send SIGINT instead.
			# self.process.terminate()
			self.process.send_signal(subprocess.signal.SIGINT)
			self.process.wait()
		finally:
			sys.stdout.write(colorama.Style.NORMAL + colorama.Fore.RESET)
		
		self.process = None
		
		# Check output file
		if not os.path.exists(self.outfile):
			print colorama.Fore.RED + 'Error: ' + colorama.Fore.RESET + 'Output file does not exist!'
			return self.outfile
		
		st = os.stat(self.outfile)
		if st.st_size == 0:
			print colorama.Fore.RED + 'Warning: ' + colorama.Fore.RESET + 'Output file size is 0!'
		
		# gstreamer produces .wav files with wrong duration information.
		# => use sox to fix that.
		# (Ignore sox warning about premature EOF on .wav input file.)
		if fix_duration:
			filename = tempfile.mktemp(suffix='.wav', prefix='fixduration-')
			sys.stdout.write(colorama.Fore.WHITE + colorama.Style.DIM)
			try:
				subprocess.check_call(['sox', self.outfile, filename])
			except Exception, e:
				print sys.stderr, e
			finally:
				sys.stdout.write(colorama.Style.NORMAL + colorama.Fore.RESET)

			shutil.move(filename, self.outfile)
		
		return self.outfile
