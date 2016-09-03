import socket
import maya.OpenMaya

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

    def _streamToMayaSublime(msg, msgType, *args):    
        msg = str(msg)
        if msgType == om.MCommandMessage.kWarning:
            msg = '# Warning: {0} #\n'.format(msg)

        elif msgType == om.MCommandMessage.kError:
            msg = '// Error: {0} //\n'.format(msg)

        elif msgType == om.MCommandMessage.kResult:
            msg = '# Result: {0} #\n'.format(msg)

        _MayaSublime_SOCK.sendto(msg, (host, port))

    cid = om.MCommandMessage.addCommandOutputCallback(_streamToMayaSublime)
    _MayaSublime_ScriptEditorOutput_CID = cid
    
