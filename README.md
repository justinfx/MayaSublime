# MayaSublime
### A Sublime Text 2/3 plugin

Send selected MEL/Python code snippets or whole files to Maya via commandPort

**Features**

* Optional streaming of all Maya Script Editor output back to Sublime console
* Maya undo support
* Includes MEL Syntax Highlighting for Sublime

----------

### Installation

**Easy Install**

You can install this plugin directly from Sublime Package Control:

https://packagecontrol.io/packages/MayaSublime

**Manual install**

1. clone this repo into the `SublimeText2/3 -> Preference -> Browse Packages` directory:  
`git clone git://github.com/justinfx/MayaSublime.git`

2. Edit the `MayaSublime.sublime-settings` file, setting the port to match the commandPorts you have configured in Maya

3. Optionally edit the keymap file to change the default hotkey from `ctrl+return` to something else.

Note - Ideally you would make your custom changes to the user settings and not the default settings, so that they do not get overwritten when the plugin is updated.

### Usage

To send a snippet, simply select some code in a MEL or python script, and hit `ctrl+return`, or right click and choose "Send To Maya".
A socket connection will be made to a running Maya instance on the configured port matching MEL or python, and the code will be 
run in Maya's environment.

As an example, if you want to open a commandPort on port 7002 for python (the default port in the config), you can do the following:

```python
# if it was already open under another configuration
cmds.commandPort(name=":7002", close=True)

# now open a new port
cmds.commandPort(name=":7002", sourceType="python")

# or open some random MEL port (make sure you change it to this port in your config file)
cmds.commandPort(name=":10000", sourceType="mel")

```

**Receiving results from Maya**

By default, results from commands sent to Maya will not returned to Sublime, so output would be viewed from Maya.
The ability to stream all output from the Maya Script Editor can be enabled in two different ways.

Edit the `MayaSublime.sublime-settings` file to make feature enabled by default:

```json
	"receive_maya_output": true
```

Or, use the Command Palette to toggle the feature on or off: "Maya: Enable ScriptEditor Output"

