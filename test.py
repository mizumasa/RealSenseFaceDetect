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

sys.path.append("/usr/local/lib")

import pyrealsense2 as rs
import cv2


OSC_PORT_OF2PY = 7110
OSC_PORT_PY2OF = 7111
SEND_ADDRESS = '127.0.0.1', OSC_PORT_PY2OF
RECV_ADDRESS = '127.0.0.1', OSC_PORT_OF2PY

FILEBASE = "/Users/sapugc/programming/of_v0.9.8_osx/apps/Art2018/MithilaPainting/bin/data/"
if not os.path.isdir(FILEBASE):
	FILEBASE = "/Users/isuca/programing/of_v0.9.8/apps/myApps/art-18hashimoto-mithila/bin/data/"

DIR_NAME = os.path.dirname(os.path.abspath(__file__))

from imgurpython import ImgurClient
import qrcode
#import pyperclip
client_id = 'd2b14e2d0051120'
client_secret = 'c354854c2797da7b7814013360bd730ff805e3af'

client_id = '8392a2213cdd164'
client_secret = 'aa081996aaa52a6d2682cc3a495b0b03e4da51bb'
client = ImgurClient(client_id, client_secret)

depth8bit_log1 = 0
depth8bit_log2 = 0
depth8bit_count = 0


def uploadImgur(filename):
	filepath = os.path.join(FILEBASE,filename)
	if os.path.exists(filepath):
		print "[PY] exec",filename
		try:
			res = client.upload_from_path(filepath)
		except:
			print "[PY] imgur upload error"
			return "none"
		print "[PY] imgur upload finihsed",filename
		#print "[PY] fileUrl",res
		if "link" in res.keys():
			img = qrcode.make(res["link"])
			qrpath = filepath.replace("/capture/","/qr/")
			img.save(qrpath)
			qrfile = qrpath.replace(FILEBASE,"")
		else:
			qrfile = "none"
	else:
		print "[PY] no such file",filepath
		qrfile = "none"
	return qrfile


class PyModule:
	def __init__(self):
		self.errorCount = 0
		self.flag = True
		self.setup()
		return
	def setup(self):
		print "[PY] client init"
		self.c = OSC.OSCClient()
		self.c.connect(SEND_ADDRESS) 
		msg = OSC.OSCMessage() 
		msg.setAddress("/status")
		msg.append("python OSC started")
		self.c.send(msg)
		print "[PY] server init"
		self.s = OSC.OSCServer(RECV_ADDRESS)
		self.s.addDefaultHandlers()
		#self.s.addMsgHandler("/bapabar/test", printing_handler)
		self.s.addMsgHandler("/image/saved", self.imageSaved)
		self.s.addMsgHandler("/cam/kick", self.camKick)
		self.s.addMsgHandler("/test", self.printMsg)
		self.s.addMsgHandler("/kill", self.kill)
		self.st = threading.Thread( target = self.s.serve_forever )
		self.st.start()

		print "[PY] server py2py test"
		self.c2 = OSC.OSCClient()
		self.c2.connect(RECV_ADDRESS) 
		msg = OSC.OSCMessage() 
		msg.setAddress("/test")
		msg.append(1)
		self.c2.send(msg)

		try:
			print "[PY] intel camera setup"
			self.pipeline = rs.pipeline()
			self.config = rs.config()
			self.config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
			self.config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
			self.pipeline.start(self.config)
		except:
			print "[PY] intel camera setup error"
			msg = OSC.OSCMessage() 
			msg.setAddress("/kill")
			msg.append(1)
			self.c2.send(msg)
			return
		print "[PY] intel camera setup done"
		
		try:
			msg = OSC.OSCMessage() 
			msg.setAddress("/cam/start")
			self.c.send(msg)
		except:
			print "[PY] error (need to setup oF server)"
			msg = OSC.OSCMessage() 
			msg.setAddress("/kill")
			msg.append(1)
			self.c2.send(msg)

		if 0:#finish in 4 sec
			time.sleep(4)
			print "[PY] server py2py test"
			self.c2 = OSC.OSCClient()
			self.c2.connect(RECV_ADDRESS) 
			msg = OSC.OSCMessage() 
			msg.setAddress("/kill")
			msg.append(1)
			self.c2.send(msg)
		return

	def imageSaved(self, addr, tags, stuff, source):
		print "---"
		print "received new osc msg from %s" % OSC.getUrlStr(source)
		print "with addr : %s" % addr
		print "typetags %s" % tags
		print "data %s" % stuff
		filename = stuff[0]
		qrname = uploadImgur(filename)
		if(qrname == "none"):
			msg2 = OSC.OSCMessage()
			msg2.setAddress("/image/uploaderror")
			msg2.append(qrname)
			self.c.send(msg2)
		msg = OSC.OSCMessage()
		msg.setAddress("/image/uploaded")
		msg.append(qrname)
		self.c.send(msg)
		return

	def printMsg(self, addr, tags, stuff, source):
		self.flag = True
		print "---"
		print "received new osc msg from %s" % OSC.getUrlStr(source)
		print "with addr : %s" % addr
		print "typetags %s" % tags
		print "data %s" % stuff
		

	def camKick(self, addr, tags, stuff, source):
		print "[PY] intel camera kick"
		frames = self.pipeline.wait_for_frames()
		depth_frame = frames.get_depth_frame()
		color_frame = frames.get_color_frame()
		if not depth_frame or not color_frame:
			return
		depth_image = np.asanyarray(depth_frame.get_data())
		color_image = np.asanyarray(color_frame.get_data())
		
		depth8bit = cv2.convertScaleAbs(depth_image[:,160:1120], alpha=0.03)
		depth8bit = np.rot90(depth8bit,3)
		global depth8bit_log1
		global depth8bit_log2
		global depth8bit_count

		if(type(depth8bit_log1) != type(1)):
			depth8bit_log2 = depth8bit_log1.copy()
		depth8bit_log1 = depth8bit.copy()
		depth8bit_count += 1
		if depth8bit_count > 2:
			h,w = depth8bit.shape
			buf = np.min(np.vstack((depth8bit.flatten(),depth8bit_log1.flatten(),depth8bit_log2.flatten())), axis=0)
			buf = buf.reshape((h,w))
			cv2.imwrite(os.path.join(DIR_NAME, "data/depth.png"), buf)
		else:
			cv2.imwrite(os.path.join(DIR_NAME, "data/depth.png"), depth8bit)

		#depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image[:,160:1120], alpha=0.03), cv2.COLORMAP_JET)
		#depth_colormap = np.rot90(depth_colormap,3)
		#cv2.imwrite(os.path.join(DIR_NAME, "data/depth.png"), depth_colormap)

		color_image = np.rot90(color_image[:,160:1120,:],3)
		cv2.imwrite(os.path.join(DIR_NAME, "data/color.png"), color_image)
		msg = OSC.OSCMessage() 
		msg.setAddress("/cam/got")
		self.c.send(msg)



	def kill(self, addr, tags, stuff, source):
		self.flag = False
		try:
			self.pipeline.stop()
			print "[PY] stop pyrealsense"
		except:
			print "[PY] error stop pyrealsense"
		print "---"
		print "received new osc msg from %s" % OSC.getUrlStr(source)
		print "with addr : %s" % addr
		print "typetags %s" % tags
		print "data %s" % stuff

	def start(self):
		print "[PY] PyModule Start"
		count = 0
		while 1:
			try:
				time.sleep(2)
				msg = OSC.OSCMessage() 
				msg.setAddress("/status")
				count += 1
				msg.append("python awake "+str(count))
				self.c.send(msg)

				if self.flag == False:
					break
			except:
				self.errorCount += 1
				print "error (need to setup oF server)", self.errorCount
				if self.errorCount > 5:
					break
		print "[PY] PyModule Stop"
		try:
			msg = OSC.OSCMessage() 
			msg.setAddress("/status")
			msg.append("[PY] python OSC goodbye")
			self.c.send(msg)
		except:
			print "[PY] goodbye error"

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
	a.start()
	pass

if __name__=='__main__':
	argvs=sys.argv
	print argvs
	main()
