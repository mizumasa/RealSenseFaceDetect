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
SEND_ADDRESS = '127.0.0.1', OSC_PORT_PY2OF
RECV_ADDRESS = '127.0.0.1', OSC_PORT_OF2PY


class PyModule:
    def __init__(self,demo=False):
        self.nowork = False
        if demo:
            self.nowork = True
        self.setup()
        self.d = {}
        return

    def send(self,msg):
        if self.nowork:
            print("No work mode",msg)
            return
        self.c.send(msg)
        return

    def setup(self):
        print "[PY] client init"
        if not self.nowork:
            self.c = OSC.OSCClient()
            self.c.connect(SEND_ADDRESS) 
        msg = OSC.OSCMessage() 
        msg.setAddress("/status")
        msg.append("python OSC started")
        self.send(msg)

        print "[PY] server init"
        self.s = OSC.OSCServer(RECV_ADDRESS)
        self.s.addDefaultHandlers()
        #self.s.addMsgHandler("/bapabar/test", printing_handler)
        #self.s.addMsgHandler("/image/saved", self.imageSaved)
        #self.s.addMsgHandler("/cam/kick", self.camKick)
        #self.s.addMsgHandler("/test", self.printMsg)
        self.s.addMsgHandler("/data", self.msg_data)

        self.s.addMsgHandler("/status", self.message)
        self.s.addMsgHandler("/kill", self.message)
        self.st = threading.Thread( target = self.s.serve_forever )
        self.st.start()
        print "[PY] setup done"

    def msg_data(self, addr, tags, stuff, source):
        print "---"
        print "received new osc msg from %s" % OSC.getUrlStr(source)
        print "with addr : %s" % addr
        print "typetags %s" % tags
        print "data %s" % stuff
        try:
            if len(stuff) > 1:
                self.d[stuff[0]] = stuff[1]
        except:
            print("error")
        return
    
    def getData(self):
        return self.d

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
        if count > 10:
            break

        msg = OSC.OSCMessage() 
        msg.setAddress("/status")
        msg.append("loop")
        a.c.send(msg)

        msg = OSC.OSCMessage() 
        msg.setAddress("/human")
        msg.append(count)
        msg.append(count)
        msg.append(count)
        a.c.send(msg)


        print(a.d)

    a.close()
    pass

if __name__=='__main__':
    argvs=sys.argv
    print argvs
    main()
