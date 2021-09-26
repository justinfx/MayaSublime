# ST2/ST3 compat
from __future__ import print_function

import re
import sys
import time
import uuid
import socket
import textwrap
import threading 
import traceback

from telnetlib import Telnet

import sublime, sublime_plugin


if sublime.version() < '3000':
	# we are on ST2 and Python 2.X
	_ST3 = False
else:
	_ST3 = True


# Our default plugin state
_settings = {

	# State of plugin settings
	'host': '127.0.0.1',
	'mel_port': 7001,
	'py_port': 7002,
	'strip_comments': True,
	'no_collisions': True,
	'maya_output': False, 
	'undo': False,

	# Internal state
	'_t_reader': None,
}

# A place to globally store a reference to our Thread
_ATTR_READER_THREAD = '_MayaSublime_Reader_Thread'


def plugin_unloaded():
	"""
	Hook called by ST3 when the plugin is unloaded
	"""
	# Clean up our thread
	reader = _settings['_t_reader']
	if reader is not None:
		reader.shutdown()
		_settings['_t_reader'] = None


class enable_maya_output(sublime_plugin.ApplicationCommand):
	
	def run(self, *args):
		_settings['maya_output'] = True
		MayaReader.set_maya_output_enabled(True)


class disable_maya_output(sublime_plugin.ApplicationCommand):
	
	def run(self, *args):
		_settings['maya_output'] = False
		MayaReader.set_maya_output_enabled(False)


class send_to_mayaCommand(sublime_plugin.TextCommand):  

	# Match single-line comments in MEL/Python
	RX_COMMENT = re.compile(r'^\s*(//|#)')

	def run(self, edit): 
		
		# Do we have a valid source language?
		syntax = self.view.settings().get('syntax')

		if re.search(r'python', syntax, re.I):
			lang = 'python'
			sep = '\n'

		elif re.search(r'mel', syntax, re.I):
			lang = 'mel'
			sep = '\r'

		else:
			print('No Maya-Recognized Language Found')
			return

		# Apparently ST3 doesn't always sync up its latest 
		# plugin settings?
		if not _settings['host']:
			sync_settings()

		# Check the current selection size to determine 
		# how we will send the source to be executed.
		selections = self.view.sel() # Returns type sublime.RegionSet
		selSize = 0
		for sel in selections:
			if not sel.empty():
				selSize += 1

		snips = []

		# If nothing is selected, we will use an approach that sends an 
		# entire source file, and tell Maya to execute it. 
		if selSize == 0:

			execType = 'execfile'

			print("Nothing Selected, Attempting to exec entire file")

			if self.view.is_dirty():
				sublime.error_message("Save Changes Before Maya Source/Import")
				return 

			file_path = self.view.file_name()
			if file_path is None:
				sublime.error_message("File must be saved before sending to Maya")
				return

			plat = sublime_plugin.sys.platform
			if plat == 'win32':
				file_path = file_path.replace('\\','\\\\')
				print("FILE PATH:",file_path)

			if lang == 'python':
				snips.append(file_path)
			else:
				snips.append('rehash; source "{0}";'.format(file_path))
		
		# Otherwise, we are sending snippets of code to be executed
		else:
			execType = 'exec'
			file_path = ''

			substr = self.view.substr
			match = self.RX_COMMENT.match
			stripComments = _settings['strip_comments']

			# Build up all of the selected lines, while removing single-line comments
			# to simplify the amount of data being sent.
			for sel in selections:
				if stripComments:
					snips.extend(line for line in substr(sel).splitlines() if not match(line))
				else:
					snips.extend(substr(sel).splitlines())

		mCmd = str(sep.join(snips))
		if not mCmd:
			return

		print('Sending {0}:\n{1!r}\n...'.format(lang, mCmd[:200]))
		
		if lang == 'python':
			# We need to wrap our source string into a template
			# so that it gets executed properly on the Maya side
			no_collide = _settings['no_collisions']
			create_undo = _settings["undo"]
			opts = dict(
				xtype=execType, cmd=mCmd, fp=file_path, 
				ns=no_collide, undo=create_undo,
				)

			mCmd = PY_CMD_TEMPLATE.format(**opts)

		if _settings["maya_output"]:
			# In case maya was restarted, we can make sure the
			# callback is always installed
			MayaReader.set_maya_output_enabled(_settings["maya_output"])

		_send_to_maya(mCmd, lang, wrap=False)


def _send_to_maya(cmd, lang='python', wrap=True, quiet=False):
	"""
	Send stringified Python code to Maya, to be executed. 
	"""
	if not _settings['host']:
		sync_settings()
		
	host = _settings['host']
	port = _settings['py_port'] if lang=='python' else _settings['mel_port']

	if lang == 'python' and wrap:
		no_collide = _settings['no_collisions']
		create_undo = _settings["undo"]
		opts = dict(xtype='exec', cmd=cmd, fp='', ns=no_collide, undo=create_undo)
		cmd = PY_CMD_TEMPLATE.format(**opts)

	c = None

	try:
		c = Telnet(host, int(port), timeout=3)
		c.write(_py_str(cmd))

	except Exception:
		e = sys.exc_info()[1]
		err = str(e)
		msg = "Failed to communicate with Maya (%(host)s:%(port)s)):\n%(err)s" % locals() 
		if quiet: 
			print(msg)
			return False

		sublime.error_message(msg)
		raise

	else:
		time.sleep(.1)
	
	finally:
		if c is not None:
			c.close()

	return True


def _py_str(s):
	"""Encode a py3 string if needed"""
	if _ST3:
		return s.encode(encoding='UTF-8')
	return s


def settings_obj():
	return sublime.load_settings("MayaSublime.sublime-settings")


_IS_SYNCING = False

def sync_settings():
	global _IS_SYNCING
	if _IS_SYNCING:
		return
	
	_IS_SYNCING = True
	try:
		_sync_settings()
	finally:
		_IS_SYNCING = False

		
def _sync_settings():
	so = settings_obj()

	_settings['host']           = so.get('maya_hostname', _settings['host'])
	_settings['py_port']        = so.get('python_command_port', _settings['py_port'])
	_settings['mel_port']       = so.get('mel_command_port', _settings['mel_port']  )
	_settings['strip_comments'] = so.get('strip_sending_comments', _settings['strip_comments'])
	_settings['no_collisions']  = so.get('no_collisions', _settings['no_collisions'])
	_settings['maya_output']    = so.get('receive_maya_output', _settings['maya_output'])
	_settings['undo']           = so.get('create_undo', _settings['undo'] )
	
	MayaReader._st2_remove_reader()

	if _settings['maya_output'] is not None:
		MayaReader.set_maya_output_enabled(_settings["maya_output"])


# A template wrapper for sending Python source safely 
# over the socket. 
# Executes in a private namespace to avoid collisions 
# with the main environment in Maya. 
# Also handles catches and printing exceptions so that
# they are not masked. 
PY_CMD_TEMPLATE = textwrap.dedent('''
	import traceback
	import __main__

	import maya.cmds

	namespace = __main__.__dict__.get('_sublime_SendToMaya_plugin')
	if not namespace:
		namespace = __main__.__dict__.copy()
		__main__.__dict__['_sublime_SendToMaya_plugin'] = namespace

	try:
		if {undo}:
			maya.cmds.undoInfo(openChunk=True, chunkName="MayaSublime Code")

		if {ns}:
			namespace['__file__'] = {fp!r}
		else:
			namespace = __main__.__dict__

		if {xtype!r} == "exec":
			exec({cmd!r}, namespace, namespace)

		else:
			with open({fp!r}, encoding='utf-8') as _fp:
				_code = compile(_fp.read(), {fp!r}, 'exec')
				exec(_code, namespace, namespace)
				
	except:
		traceback.print_exc() 
	finally:
		if {undo}:
			maya.cmds.undoInfo(closeChunk=True)
''')



PY_MAYA_CALLBACK = textwrap.dedent(r'''
import sys
import errno
import socket
import maya.OpenMaya

try:
	from io import StringIO
except ImportError:
	try:
		from cStringIO import StringIO
	except ImportError:
		from StringIO import StringIO

if '_MayaSublime_ScriptEditorOutput_CID' not in globals():
	_MayaSublime_ScriptEditorOutput_CID = None

if '_MayaSublime_SOCK' not in globals():
	_MayaSublime_SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def _MayaSublime_streamScriptEditor(enable, host="127.0.0.1", port=5123, quiet=False):
	om = maya.OpenMaya 

	global _MayaSublime_ScriptEditorOutput_CID
	cid = _MayaSublime_ScriptEditorOutput_CID

	# Only print if we are really changing state
	if enable and cid is None:
		sys.stdout.write("[MayaSublime] Enable Streaming ScriptEditor " \
						 "({0}:{1})\n".format(host, port))

	elif not enable and cid is not None:
		sys.stdout.write("[MayaSublime] Disable Streaming ScriptEditor\n")

	if cid is not None:
		om.MMessage.removeCallback(cid)
		_MayaSublime_ScriptEditorOutput_CID = None 

	if not enable:
		return 

	buf = StringIO()

	def _streamToMayaSublime(msg, msgType, *args): 
		buf.seek(0)
		buf.truncate()
		
		if msgType != om.MCommandMessage.kDisplay:
			buf.write('[MayaSublime] ')

		if msgType == om.MCommandMessage.kWarning:
			buf.write('# Warning: ')
			buf.write(msg)
			buf.write(' #\n')

		elif msgType == om.MCommandMessage.kError:
			buf.write('// Error: ')
			buf.write(msg)
			buf.write(' //\n')

		elif msgType == om.MCommandMessage.kResult:
			buf.write('# Result: ')
			buf.write(msg)
			buf.write(' #\n')

		else:
			buf.write(msg)

		buf.seek(0)

		# Start with trying to send 8kb packets
		bufsize = 8*1024

		# Loop until the buffer is empty
		while True:

			while bufsize > 0:
				# Save our position in case we error
				# and need to roll back
				pos = buf.tell()

				part = buf.read(bufsize)
				if not part:
					# Buffer is empty. Nothing else to send
					return 

				try:
					_MayaSublime_SOCK.sendto(_py_str(part), (host, port))

				except Exception as e:
					if e.errno == errno.EMSGSIZE:
						# We have hit a message size limit. 
						# Scale down and try the packet again
						bufsize /= 2
						if bufsize < 1:
							raise
						buf.seek(pos)
						continue 
					# Some other error
					raise 

				# Message sent without error
				break

	cid = om.MCommandMessage.addCommandOutputCallback(_streamToMayaSublime)
	_MayaSublime_ScriptEditorOutput_CID = cid
''')


class MayaReader(threading.Thread):
	"""
	A threaded reader that monitors for published ScriptEditor
	output from Maya. 

	Installs a ScriptEditor callback to Maya to produce messages.
	"""

	# Max number of bytes to read from each packet.
	BUFSIZE = 64 * 1024 # 64KB is max UDP packet size

	# Signal to stop a receiving MayaReader
	STOP_MSG = _py_str('MayaSublime::MayaReader::{0}'.format(uuid.uuid4()))

	# # Stringified ScriptEditor callback code to install in Maya
	# PY_MAYA_CALLBACK = open(os.path.join(os.path.dirname(__file__), 
	# 								     "lib/pubScriptEditor.py")).read()
	PY_MAYA_CALLBACK = PY_MAYA_CALLBACK

	def __init__(self, host='127.0.0.1', port=0):
		super(MayaReader, self).__init__()

		self.daemon = True

		self._running = threading.Event()
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.bind((host, port))        

	def port(self):
		"""Get the port number being used by the socket"""
		_, port = self.sock.getsockname()
		return port

	def is_running(self): 
		"""Return true if the thread is running"""
		return self._running.is_set()

	def shutdown(self):
		"""Stop the monitoring of Maya output"""
		self._running.clear()
		# Send shutdown message to local UDP
		self.sock.sendto(self.STOP_MSG, self.sock.getsockname())

	def run(self):    
		prefix = '[MayaSublime] '

		print("{0}started on port {1}".format(prefix, self.port()))

		fails = 0
		self._running.set()

		while  self._running.is_set():
			try:
				msg, addr = self.sock.recvfrom(self.BUFSIZE)

			except Exception as e:
				print("Failed while reading output from Maya:")
				traceback.print_exc()

				# Prevent runaway failures from spinning
				fails += 1
				if fails >= 10:
					# After too many failures in a row
					# wait a bit
					fails = 0
					time.sleep(5)

				continue

			fails = 0 

			if msg == self.STOP_MSG:
				break 

			if _ST3:
				msg = msg.decode()

			sys.stdout.write(msg)
		
		print("{0}MayaReader stopped".format(prefix))

	def _set_maya_callback_enabled(self, enable, quiet=False):
		"""
		Enable or disable the actual publishing of ScriptEditor output from Maya
		"""
		host, port = self.sock.getsockname()
		cmd = "_MayaSublime_streamScriptEditor({0}, host={1!r}, port={2})".format(enable, host, port)
		return _send_to_maya(cmd, quiet=quiet, wrap=_settings['no_collisions'])

	@classmethod
	def _st2_remove_reader(cls):
		"""
		A hack to work around SublimeText2 not having a 
		module level hook for when the plugin is loaded
		and unloaded. 
		Need to store a reference to our thread that doesn't
		get blown away when the plugin reloads, so that we
		can clean it up.
		"""
		if _ST3:
			return 

		import __main__

		reader = getattr(__main__, _ATTR_READER_THREAD, None)
		if reader:
			reader.shutdown()
			setattr(__main__, _ATTR_READER_THREAD, None)

	@classmethod
	def _st2_replace_reader(cls, reader):
		"""
		A hack to work around SublimeText2 not having a 
		module level hook for when the plugin is loaded
		and unloaded. 
		Need to store a reference to our thread that doesn't
		get blown away when the plugin reloads, so that we
		can clean it up and replace it with another.
		"""
		if _ST3:
			return 
			
		cls._st2_remove_reader()

		import __main__
		setattr(__main__, _ATTR_READER_THREAD, reader)

	@classmethod 
	def install_maya_callback(cls):
		"""Send the callback logic to Maya"""
		return _send_to_maya(cls.PY_MAYA_CALLBACK, quiet=True, wrap=_settings['no_collisions'])

	@classmethod
	def set_maya_output_enabled(cls, enable):
		# Make sure the Maya filtering callback code
		# is set up already
		ok = cls.install_maya_callback()
		quiet = not ok

		reader = _settings.get('_t_reader')

		# handle disabling the reader
		if not enable:
			if reader:
				reader.shutdown()
				reader._set_maya_callback_enabled(False, quiet)
			return

		# handle enabling the reader
		if reader and reader.is_alive():
			# The reader is already running
			reader._set_maya_callback_enabled(True, quiet)
			return

		# Start the reader
		reader = cls()
		reader.start()
		_settings['_t_reader'] = reader

		cls._st2_replace_reader(reader)

		reader._set_maya_callback_enabled(True, quiet)


# Add callbacks for monitoring setting changes
settings_obj().clear_on_change("MayaSublime.settings")
settings_obj().add_on_change("MayaSublime.settings", sync_settings)
sync_settings()
