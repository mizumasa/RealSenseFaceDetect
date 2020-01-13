#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#内容
#auther:mizuochi
#from 11/11/

import sys
import os
import numpy as np
import json
import random
import time
import pprint
import OSC
import time, random
import threading

OSC_PORT_OF2PY = 7110
OSC_PORT_PY2OF = 7111
SEND_ADDRESS = '127.0.0.1', OSC_PORT_OF2PY
RECV_ADDRESS = '127.0.0.1', OSC_PORT_PY2OF


class PyModule:
    def __init__(self):
        self.setup()
        return

    def setup(self):
        print "[PY] client init"
        self.c = OSC.OSCClient()
        self.c.connect(SEND_ADDRESS) 


        print "[PY] server init"
        self.s = OSC.OSCServer(RECV_ADDRESS)
        self.s.addDefaultHandlers()
        #self.s.addMsgHandler("/bapabar/test", printing_handler)
        #self.s.addMsgHandler("/image/saved", self.imageSaved)
        #self.s.addMsgHandler("/cam/kick", self.camKick)
        #self.s.addMsgHandler("/test", self.printMsg)
        self.s.addMsgHandler("/human", self.message)
        self.s.addMsgHandler("/toio", self.message)
        
        self.s.addMsgHandler("/status", self.message)
        self.s.addMsgHandler("/kill", self.message)
        self.st = threading.Thread( target = self.s.serve_forever )
        self.st.start()

    def message(self, addr, tags, stuff, source):
        print "---"
        print "received new osc msg from %s" % OSC.getUrlStr(source)
        print "with addr : %s" % addr
        print "typetags %s" % tags
        print "data %s" % stuff

    def close(self):
        self.s.close()
        self.st.join()
        return


def printing_handler(addr, tags, stuff, source):
    print "---"
    print "received new osc msg from %s" % OSC.getUrlStr(source)
    print "with addr : %s" % addr
    print "typetags %s" % tags
    print "data %s" % stuff


def main():
    a = PyModule()
    count = 0
    while 1:
        print("loop")
        time.sleep(1)
        count += 1
        if count > 20:
            break

        try:
            if 1 and count > 4:
                msg = OSC.OSCMessage() 
                msg.setAddress("/data")
                msg.append("loop")
                msg.append(count)
                a.c.send(msg)
        except:
            a.close()

    a.close()
    pass

if __name__=='__main__':
    argvs=sys.argv
    print argvs
    main()
