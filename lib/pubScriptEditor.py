import sys
import errno
import socket
import maya.OpenMaya

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
                    _MayaSublime_SOCK.sendto(part, (host, port))

                except Exception as e:
                    if e.errno == errno.EMSGSIZE:
                        # We have hit a message size limit. 
                        # Scale down and try the packet again
                        bufsize /= 2
                        buf.seek(pos)
                        continue 
                    # Some other error
                    raise 

                # Message sent without error
                break

    cid = om.MCommandMessage.addCommandOutputCallback(_streamToMayaSublime)
    _MayaSublime_ScriptEditorOutput_CID = cid
    
