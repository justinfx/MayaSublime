import sublime, sublime_plugin  
from telnetlib import Telnet
import time
import re

_settings = {
	'port': 7001,
}

class SendToMayaCommand(sublime_plugin.TextCommand):  

	CMD_TEMPLATE = "import __main__; exec('''%s''', __main__.__dict__, __main__.__dict__)"

	def run(self, edit):  
		snips = []
		for sel in self.view.sel():
			snips.extend(line for line in re.split(r'[\r\n]+', self.view.substr(sel)) 
							if not line.startswith('#'))

		cmd = '\n'.join(snips)
		if not cmd:
			return
		print cmd

		mCmd = self.CMD_TEMPLATE % str(cmd)

		try:
			c = Telnet("", int(_settings['port']), timeout=3)
			c.write(mCmd)
		except Exception, e:
			sublime.error_message("Failed to communicate with Maya:\n%s" % str(e))
			raise
		else:
			time.sleep(.1)
		finally:
			c.close()


def settings_obj():
	return sublime.load_settings("MayaSublime.sublime-settings")

def sync_settings():
	global _settings
	so = settings_obj()
	_settings['port'] = so.get('python_command_port')
	


settings_obj().clear_on_change("MayaSublime.settings")
settings_obj().add_on_change("MayaSublime.settings", sync_settings)
sync_settings()