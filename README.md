# MayaSublime
### A Sublime Text 2 plugin

Send selected MEL/Python code snippets to Maya via commandPort

----------

### Installation

1. clone this repo into the `SublimeText2 -> Preference -> Browse Packages` directory:  
`git clone git://github.com/justinfx/MayaSublime.git`

2. Edit the `MayaSublime.sublime-settings` file, setting the port to match the commandPorts you have configured in Maya

3. Optionally edit the keymap file to change the default hotkey from `ctrl+return` to something else.

### Usage

Simply select some code in a mel or python script, and hit `ctrl+return`. 
A socket conncetion will be made to a running Maya instance on the configured port matching mel or python, and the code will be 
run in Maya's environment.