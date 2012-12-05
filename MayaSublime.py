import sublime, sublime_plugin  
from telnetlib import Telnet
import time
import re
import os.path

_settings = {
	'host'		: '127.0.0.1',
	'mel_port'	: 7001,
	'py_port'	: 7002
}

class SendToMayaCommand(sublime_plugin.TextCommand):  

	PY_CMD_TEMPLATE = "import traceback\nimport __main__\ntry:\n\texec('''%s''', __main__.__dict__, __main__.__dict__)\nexcept:\n\ttraceback.print_exc()"

	def run(self, edit): 

		
		syntax = self.view.settings().get('syntax')

		if re.search(r'python', syntax, re.I):
			lang = 'python'
		elif re.search(r'mel', syntax, re.I):
			lang = 'mel'
		else:
			print 'No Maya Recognized Language Found'
			return		

		host = _settings['host'] 
		port = _settings['py_port'] if lang=='python' else _settings['mel_port']

		selections = self.view.sel() # Returns type sublime.RegionSet
		selSize = 0
		for sel in selections:
			if not sel.empty():
				selSize += 1

		snips = []

		if selSize == 0:
			print "Nothing Selected, Attempting to Source/Import Current File"
			if self.view.is_dirty():
				sublime.error_message("Save Changes Before Maya Source/Import")
			else:
				file_path = self.view.file_name()
				if file_path is not None:
					file_name = os.path.basename(file_path)
					module_name = os.path.splitext(file_name)[0]
					
					if lang == 'python':
						snips.append('import {0}\nreload({0})'.format(module_name))
					else:
						snips.append('rehash; source {0};'.format(module_name))
					#print "SNIPS:", snips
		
		for sel in selections:
			snips.extend(line.replace(r"'''", r"\'\'\'") for line in 
							re.split(r'[\r]+', self.view.substr(sel)) 
							if not re.match(r'^//|#', line))

		mCmd = str('\n'.join(snips))
		if not mCmd:
			return
		
		print 'Sending:\n%s...\n' % mCmd[:200]

		if lang == 'python':
			mCmd = self.PY_CMD_TEMPLATE % mCmd

		c = None

		try:
			c = Telnet(host, int(port), timeout=3)
			c.write(mCmd)
		except Exception, e:
			err = str(e)
			sublime.error_message(
				"Failed to communicate with Maya (%(host)s:%(port)s)):\n%(err)s" % locals()
			)
			raise
		else:
			time.sleep(.1)
		finally:
			if c is not None:
				c.close()


def settings_obj():
	return sublime.load_settings("MayaSublime.sublime-settings")

def sync_settings():
	global _settings
	so = settings_obj()
	_settings['host'] 		= so.get('maya_hostname')
	_settings['py_port'] 	= so.get('python_command_port')
	_settings['mel_port'] 	= so.get('mel_command_port')
	


settings_obj().clear_on_change("MayaSublime.settings")
settings_obj().add_on_change("MayaSublime.settings", sync_settings)
sync_settings()