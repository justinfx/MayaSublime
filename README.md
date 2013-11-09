# MayaSublime
### A Sublime Text 2/3 plugin

Send selected MEL/Python code snippets or whole files to Maya via commandPort

----------

### Installation

1. clone this repo into the `SublimeText2 -> Preference -> Browse Packages` directory:  
`git clone git://github.com/justinfx/MayaSublime.git`

2. Edit the `MayaSublime.sublime-settings` file, setting the port to match the commandPorts you have configured in Maya

3. Optionally edit the keymap file to change the default hotkey from `ctrl+return` to something else.

### Usage

To send a snippet, simply select some code in a mel or python script, and hit `ctrl+return`, or right click and choose "Send To Maya".
A socket conncetion will be made to a running Maya instance on the configured port matching mel or python, and the code will be 
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
