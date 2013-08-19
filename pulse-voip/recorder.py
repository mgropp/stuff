import subprocess
import os
import tempfile

class PulseRecorder(object):
	"""
	Use gstreamer to record two PulseAudio streams to a PCM wave file.
	"""
	def __init__(self):
		self.process = None
	
	
	def is_recording(self):
		return not self.process is None
	
	
	def record(self, source1, source2, outfile):
		if not self.process is None:
			raise Exception('Already recording!')
		
		self.outfile = outfile
		self.process = subprocess.Popen([
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
		])
	
	
	def stop(self, fix_duration=True):
		if self.process is None:
			return
		
		self.process.terminate()
		self.process.wait()
		self.process = None
		
		if fix_duration:
			filename = tempfile.mktemp(suffix='.wav', prefix='fixduration-')
			subprocess.check_call(['sox', self.outfile, filename])
			os.rename(filename, self.outfile)
