# ST2/ST3 compat
import sublime, sublime_plugin
from telnetlib import Telnet
import time
import re
import textwrap
import os.path
import sys

if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
else:
	_ST3 = True

_settings = {
	'host'      : '127.0.0.1',
	'mel_port'  : 7001,
	'py_port'   : 7002
}

class send_to_mayaCommand(sublime_plugin.TextCommand):  

	PY_CMD_TEMPLATE = textwrap.dedent('''
		import traceback
		import __main__

		namespace = __main__.__dict__.get('_sublime_SendToMaya_plugin')
		if not namespace:
			namespace = __main__.__dict__.copy()
			__main__.__dict__['_sublime_SendToMaya_plugin'] = namespace

		namespace['__file__'] = {2!r}

		try:
			{0}({1!r}, namespace, namespace)
		except:
			traceback.print_exc() 
	''')

	RX_COMMENT = re.compile(r'^\s*(//|#)')

	def run(self, edit): 
		
		syntax = self.view.settings().get('syntax')

		if re.search(r'python', syntax, re.I):
			lang = 'python'
			sep = '\n'

		elif re.search(r'mel', syntax, re.I):
			lang = 'mel'
			sep = ' '

		else:
			print ('No Maya Recognized Language Found')
			return

		isPython = (lang=='python')

		host = _settings['host']
		port = _settings['py_port'] if lang=='python' else _settings['mel_port']

		selections = self.view.sel() # Returns type sublime.RegionSet
		selSize = 0
		for sel in selections:
			if not sel.empty():
				selSize += 1

		snips = []

		if selSize == 0:

			execType = 'execfile'

			print ("Nothing Selected, Attempting to exec entire file")

			if self.view.is_dirty():
				sublime.error_message("Save Changes Before Maya Source/Import")
				return 

			plat = sublime_plugin.sys.platform
			file_path = self.view.file_name()
			if file_path is None:
				sublime.error_message("File must be saved before sending to Maya")
				return

			if plat == 'win32':
				file_path = file_path.replace('\\','\\\\')
				print("FILE PATH:",file_path)

			if lang == 'python':
				snips.append(file_path)
			else:
				snips.append('rehash; source "{0}";'.format(file_path))
		
		else:
			execType = 'exec'
			file_path = ''

			for sel in selections:
				snips.extend((line if isPython else line.strip()) 
								for line in self.view.substr(sel).splitlines() 
								if not self.RX_COMMENT.match(line))

		mCmd = str(sep.join(snips))
		if not mCmd:
			return

		print ('Sending:\n{0} ...\n',format(mCmd)[:200])
		
		if lang == 'python':
			mCmd = self.PY_CMD_TEMPLATE.format(execType, mCmd, file_path)

		c = None

		try:
			c = Telnet(host, int(port), timeout=3)
			if _ST3:
				c.write(mCmd.encode(encoding='UTF-8'))
			else:
				c.write(mCmd)


		except Exception:
			e = sys.exc_info()[1]
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
	_settings['host']       = so.get('maya_hostname')
	_settings['py_port']    = so.get('python_command_port')
	_settings['mel_port']   = so.get('mel_command_port')
	


settings_obj().clear_on_change("MayaSublime.settings")
settings_obj().add_on_change("MayaSublime.settings", sync_settings)
sync_settings()