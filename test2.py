#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os,sys
import time
import cv2
import numpy as np
from lib_gphoto2 import LIB_GPHOTO2,ZAF_H,ZAF_W,ZAF_OUT_H,ZAF_OUT_W
from lib_gui import LIB_GUI
import lib_image as li
from zaf_usb_filter_talker import zaf_usb_filter

from multiprocessing import Process
from multiprocessing import Pipe
from multiprocessing import Array

PTP_FRAME_H = 576
PTP_FRAME_W = 1024
META_SIZE = 4
META_SCALE = 4
AKAZE_DIM = 64 #x,y,size,akaze=61
DESC_MAX_NUM = 1000

ZAF_SCALE = 8
CAM_TEST1 = False
CAM_TEST2 = False
DEBUG_SHOW = False

def valueToNdarray(v):
    return np.ctypeslib.as_array(v.get_obj())

def valueToDesc(v):
    arr = valueToNdarray(v).reshape((DESC_MAX_NUM,AKAZE_DIM))
    kpnum = int(arr[0,0])
    des = arr[1:kpnum+1,3:].astype("uint8")
    kp=[]
    for i in range(kpnum):
        kp.append(cv2.KeyPoint(arr[i+1,0],arr[i+1,1],arr[i+1,2]))
    return kp,des    
    
def descToValue(kp,des,v,offsetx=0,offsety=0):
    arr = valueToNdarray(v).reshape((DESC_MAX_NUM,AKAZE_DIM))
    kpnum = min(len(kp),DESC_MAX_NUM-1)
    arr[0,0] = kpnum
    arr[0,1] = offsetx
    arr[0,2] = offsety
    for i in range(kpnum):
        arr[i+1,0] = kp[i].pt[0]
        arr[i+1,1] = kp[i].pt[1]
        arr[i+1,2] = kp[i].size
    if kpnum>0:
        arr[1:kpnum+1,3:] = des[:kpnum,:]
    arr[1:kpnum+1,0] += offsetx
    arr[1:kpnum+1,1] += offsety


def Process1(ptomain,maintop,frame_conn):
    WM = zaf_usb_filter()
    cam = LIB_GPHOTO2()
    if CAM_TEST1:cam.setDummy()
    cam.setup(0)
    camNum = cam.getNumOfDevices()
    print(str(camNum)+" cameras")
    elapsed_times = []
    count = 0
    g = LIB_GUI()
    g.setup()
    try:
        while True:
            event, values = g.read()
            if event == 'Save':
                f = open('param.json', 'w')
                json.dump(values, f)
                f.close()
            if event == 'Exit' or event is None:
                g.close()
                cam.close()
                ptomain.send({"exit":None})
                break
            start = time.time()
            for i in range(camNum):
                img,zaf,info = cam.read(i)
                gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
                #gray[:,:]=0
                #kp, des = akaze.detectAndCompute(gray,None)
                #gray = cv2.drawKeypoints(gray, kp, None)
                #if DEBUG_SHOW:cv2.imshow("img"+str(i),img)
                if DEBUG_SHOW:cv2.imshow("img"+str(i),gray)
                #start2 = time.time()
                #ptomain.send({"frame":gray})
                #print("time to send",time.time()-start2)
                if DEBUG_SHOW:cv2.imshow("zaf"+str(i),cv2.resize(zaf,(ZAF_W*10,ZAF_H*10),interpolation=cv2.INTER_NEAREST))
                
                zaf_wm, img_blend = WM.ImageCallback(img,zaf,info)
                zaf_view = cv2.resize(zaf_wm,(ZAF_OUT_W*ZAF_SCALE,ZAF_OUT_H*ZAF_SCALE),interpolation=cv2.INTER_NEAREST)
                if DEBUG_SHOW:cv2.imshow("zaf wm"+str(i),zaf_view)
                mask = li.clip(zaf_wm, values["back"],values["front"])
                l,t,r,b = li.estimateRect(mask)
                ll,tt,rr,bb = li.rectFrameScale(l,t,r,b,ZAF_OUT_H,ZAF_OUT_W,PTP_FRAME_H,PTP_FRAME_W,META_SCALE)
                valueToNdarray(frame_conn)[:] = np.hstack((gray.flatten(),[ll,tt,rr,bb]))
                mask_view = np.uint8(mask*255)
                mask_view = cv2.resize(mask_view,(ZAF_OUT_W*ZAF_SCALE,ZAF_OUT_H*ZAF_SCALE),interpolation=cv2.INTER_NEAREST)
                cv2.rectangle(mask_view, (l*ZAF_SCALE, t*ZAF_SCALE), (r*ZAF_SCALE, b*ZAF_SCALE), (255, 0, 0))
                if DEBUG_SHOW:cv2.imshow("zaf mask"+str(i),mask_view)
                if img_blend is not None:
                    if 1:cv2.imshow("img blend"+str(i),img_blend)
                key = cv2.waitKey(1)
                if key == ord(" "):
                    break
            elapsed_times.append(time.time() - start)
            if count%24 == 0:
                print ("elapsed_time(FBS):{0:.0f}".format(sum(elapsed_times)/24.*1000) + "[msec] {0:.0f}[fps]".format(24. / sum(elapsed_times)))
                elapsed_times = []
            start = time.time()
            count += 1

    except KeyboardInterrupt:
        cam.close()

def Process1_2(ptomain,maintop,frame_conn,kp_conn):
    akaze = cv2.AKAZE_create()
    while True:
        frame = valueToNdarray(frame_conn).astype("uint8")
        l = frame[-4]*META_SCALE
        t = frame[-3]*META_SCALE
        r = frame[-2]*META_SCALE
        b = frame[-1]*META_SCALE
        frame = frame[:-META_SIZE].reshape((PTP_FRAME_H,PTP_FRAME_W))
        while maintop.poll():
            recv = maintop.recv()
            if "exit" in recv.keys():
                return
        if t<b and l<r:
            frame = frame[t:b,l:r]
        #print("crop",frame.shape)
        kp, des = akaze.detectAndCompute(frame,None)
        descToValue(kp,des,kp_conn,offsetx=l,offsety=t)
        frame = cv2.drawKeypoints(frame, kp, None)
        #print("akaze",frame.shape)
        if DEBUG_SHOW:cv2.imshow("akaze",frame)
        cv2.imshow("akaze",frame)
        key = cv2.waitKey(1)


def Process2(ptomain,maintop,frame_conn):
    WM = zaf_usb_filter()
    cam = LIB_GPHOTO2()
    if CAM_TEST2:cam.setDummy(1)
    cam.setup(1)
    camNum = cam.getNumOfDevices()
    print(str(camNum)+" cameras")
    elapsed_times = []
    count = 0
    try:
        while True:
            start = time.time()
            while maintop.poll():
                recv = maintop.recv()
                if "exit" in recv.keys():
                    return
            for i in range(camNum):
                img,zaf,info = cam.read(i)
                gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
                if DEBUG_SHOW:cv2.imshow("img2 "+str(i),gray)
                valueToNdarray(frame_conn)[:-META_SIZE] = gray.flatten()
                if DEBUG_SHOW:cv2.imshow("zaf2 "+str(i),cv2.resize(zaf,(ZAF_W*10,ZAF_H*10),interpolation=cv2.INTER_NEAREST))
                #zaf_wm, img_blend = WM.ImageCallback(img,zaf,info)
                #zaf_view = cv2.resize(zaf_wm,(ZAF_OUT_W*ZAF_SCALE,ZAF_OUT_H*ZAF_SCALE),interpolation=cv2.INTER_NEAREST)
                #if DEBUG_SHOW:cv2.imshow("zaf2 wm"+str(i),zaf_view)
                key = cv2.waitKey(1)
                if key == ord(" "):
                    break
            elapsed_times.append(time.time() - start)
            if count%24 == 0 and 0:
                print ("elapsed_time 2 (FBS):{0:.0f}".format(sum(elapsed_times)/24.*1000) + "[msec] {0:.0f}[fps]".format(24. / sum(elapsed_times)))
                elapsed_times = []
            start = time.time()
            count += 1

    except KeyboardInterrupt:
        cam.close()

def Process2_2(ptomain,maintop,frame_conn,kp_conn):
    akaze = cv2.AKAZE_create()
    while True:
        frame = valueToNdarray(frame_conn).astype("uint8")[:-META_SIZE].reshape((PTP_FRAME_H,PTP_FRAME_W))
        while maintop.poll():
            recv = maintop.recv()
            if "exit" in recv.keys():
                return
        kp, des = akaze.detectAndCompute(frame,None)
        descToValue(kp,des,kp_conn)
        frame = cv2.drawKeypoints(frame, kp, None)
        #print("akaze2 ",frame.shape)
        if DEBUG_SHOW:cv2.imshow("akaze2 ",frame)
        key = cv2.waitKey(1)


def main(argv):
    if "test1" in argv:
        global CAM_TEST1
        CAM_TEST1 = True
    if "test2" in argv:
        global CAM_TEST2
        CAM_TEST2 = True
    if "debug" in argv:
        global DEBUG_SHOW
        DEBUG_SHOW = True
    parent_maintop1, child_maintop1 = Pipe()
    parent_ptomain1, child_ptomain1 = Pipe()
    frame_conn1 = Array('i',np.zeros((PTP_FRAME_H*PTP_FRAME_W+META_SIZE),dtype="uint8"))
    p1 = Process(target = Process1, args=(child_ptomain1, parent_maintop1, frame_conn1))
    p1.start()
    
    parent_maintop1_2, child_maintop1_2 = Pipe()
    parent_ptomain1_2, child_ptomain1_2 = Pipe()
    kp_conn1 = Array('i',np.zeros((DESC_MAX_NUM*AKAZE_DIM),dtype="uint16"))
    p1_2 = Process(target = Process1_2, args=(child_ptomain1_2, parent_maintop1_2, frame_conn1, kp_conn1))
    p1_2.start()
    
    parent_maintop2, child_maintop2 = Pipe()
    parent_ptomain2, child_ptomain2 = Pipe()
    frame_conn2 = Array('i',np.zeros((PTP_FRAME_H*PTP_FRAME_W+META_SIZE),dtype="uint8"))
    p2 = Process(target = Process2, args=(child_ptomain2, parent_maintop2, frame_conn2))
    p2.start()

    parent_maintop2_2, child_maintop2_2 = Pipe()
    parent_ptomain2_2, child_ptomain2_2 = Pipe()
    kp_conn2 = Array('i',np.zeros((DESC_MAX_NUM*AKAZE_DIM),dtype="uint16"))
    p2_2 = Process(target = Process2_2, args=(child_ptomain2_2, parent_maintop2_2, frame_conn2, kp_conn2))
    p2_2.start()

    """FLANN_INDEX_KDTREE = 0
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks=50)   # or pass empty dictionary
    flann = cv2.FlannBasedMatcher(index_params,search_params)
    """
    bf = cv2.BFMatcher(crossCheck=True)
    print("process start")
    loop = True
    count = 0
    while loop:
        #frame = np.zeros((1080,1920))
        #for i in range(1080):
        #    for j in range(1920):
        #        frame[i,j]=(i*j)%256
        #print("loop")
        count+=1
        while parent_ptomain1.poll():
            d = parent_ptomain1.recv()
            if "exit" in d.keys():
                print("got conn exit")
                child_maintop1_2.send(d)
                child_maintop2.send(d)
                child_maintop2_2.send(d)
                loop = False
        time.sleep(0.1)
        try:
            kp1,des1 = valueToDesc(kp_conn1)
            kp2,des2 = valueToDesc(kp_conn2)
            print(len(kp1),len(kp2),"keypoint")
            matches = bf.match(des1,des2)
            #matches = flann.knnMatch(des1,des2,k=2)
            """
            matchesMask = [[0,0] for i in range(len(matches))]
            for i,(m,n) in enumerate(matches):
                if m.distance < 0.7*n.distance:
                    matchesMask[i]=[1,0]
            draw_params = dict(matchColor = (0,255,0),
                            singlePointColor = (255,0,0),
                            matchesMask = matchesMask,
                            flags = 0)
            """
            print("matches",len(matches))
            img1 = valueToNdarray(frame_conn1).astype("uint8")[:-META_SIZE].reshape((PTP_FRAME_H,PTP_FRAME_W))
            img2 = valueToNdarray(frame_conn2).astype("uint8")[:-META_SIZE].reshape((PTP_FRAME_H,PTP_FRAME_W))
            #img3 = cv2.drawMatchesKnn(img1,kp1,img2,kp2,matches,None,**draw_params)
            img3 = cv2.drawMatches(img1,kp1,img2,kp2,matches,None,flags=2)
            cv2.imshow("match",cv2.resize(img3,(800,225)))
            key = cv2.waitKey(1)
        except:
            print("error matching")

    p1.join()
    p1_2.join()
    p2.join()
    p2_2.join()
    print("process finish")

if __name__ == "__main__":
    argvs=sys.argv
    print(argvs)
    main(argvs)
