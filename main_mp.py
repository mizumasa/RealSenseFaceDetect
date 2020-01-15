#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os,sys
import time
import cv2
import numpy as np
import realsense_face_detect as rs
import osc_of
import OSC
import dlib

from LowPassFilter import LowPassFilter
from multiprocessing import Process
from multiprocessing import Pipe
from multiprocessing import Array

cutoff_hz = 1.0
dt = 1.0/30

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


def Process1(ptomain,maintop,frame_conn,frame_conn_res):
    elapsed_times = []
    count = 0
    detector = dlib.get_frontal_face_detector()
    print("Process 1 start")
    try:
        maxl = 0
        maxt = 0
        maxr = 0
        maxb = 0
        while True:
            #event, values = g.read()
            #if event == 'Save':
            #    f = open('param.json', 'w')
            #    json.dump(values, f)
            #    f.close()
            #if event == 'Exit' or event is None:
            #    g.close()
            #    ptomain.send({"exit":None})
            #    break
            while maintop.poll():
                recv = maintop.recv()
                if "exit" in recv.keys():
                    return
            start = time.time()
            img_rgb = valueToNdarray(frame_conn).astype("uint8")
            img_rgb = img_rgb.reshape((rs.CAM_H,rs.CAM_W,3))
            maxSize = 0
            dets, scores, idx = detector.run(img_rgb, 0)
            for det in dets:
                #cv2.rectangle(img_rgb, (det.left(), det.top()), (det.right(), det.bottom()), (0, 0, 255))
                w = det.right() - det.left()
                h = det.bottom() - det.top()
                if max(w,h)>maxSize:
                    maxl = det.left()
                    maxt = det.top()
                    maxr = det.right()
                    maxb = det.bottom()
                    maxSize = max(w,h)
            if maxSize > 20:
                valueToNdarray(frame_conn_res)[:] = img_rgb.flatten()
                ptomain.send({"face":[maxl,maxt,maxr,maxb]})
            #cv2.imshow("dlib",cv2.resize(img_rgb,(640,360)))
            key = cv2.waitKey(1)
            if key == ord(" "):
                break
            elapsed_times.append(time.time() - start)
            if count%24 == 0:
                print ("elapsed_time(FBS):{0:.0f}".format(sum(elapsed_times)/24.*1000) + "[msec] {0:.0f}[fps]".format(24. / sum(elapsed_times)))
                elapsed_times = []
            start = time.time()
            count += 1
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Process 1 Error")
        pass

def main(argv):
    if "debug" in argv:
        global DEBUG_SHOW
        DEBUG_SHOW = True
    parent_maintop1, child_maintop1 = Pipe()
    parent_ptomain1, child_ptomain1 = Pipe()
    frame_conn1 = Array('i',np.zeros((rs.CAM_W*rs.CAM_H*3),dtype="uint8"))
    frame_conn2 = Array('i',np.zeros((rs.CAM_W*rs.CAM_H*3),dtype="uint8"))
    p1 = Process(target = Process1, args=(child_ptomain1, parent_maintop1, frame_conn1, frame_conn2))
    p1.start()
    cam = rs.RS_FACE(dlib=False)
    detl = 0
    dett = 0
    detr = 0
    detb = 0
    tracker = dlib.correlation_tracker()
    track = False
    LPF = LowPassFilter()
    LPF.set_param(np.zeros(5),cutoff_hz,dt)

    output_x_lpf = 0
    output_y_lpf = 0
    output_z_lpf = 0
    
    while 1:
        ret = cam.read()
        if ret is not None:
            color,depth = ret
            img_rgb = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
            valueToNdarray(frame_conn1)[:] = img_rgb.flatten()

            cv2.rectangle(color, (detl, dett), (detr, detb), (0, 0, 255))

            while parent_ptomain1.poll():
                d = parent_ptomain1.recv()
                if "face" in d.keys():
                    img_rgb_res = valueToNdarray(frame_conn2).astype("uint8")
                    img_rgb_res = img_rgb_res.reshape((rs.CAM_H,rs.CAM_W,3))
                    img_bgr_res = cv2.cvtColor(img_rgb_res, cv2.COLOR_BGR2RGB)
                    print("got conn face",d["face"])
                    detl = d["face"][0]
                    dett = d["face"][1]
                    detr = d["face"][2]
                    detb = d["face"][3]
                    w = detr - detl
                    h = detb - dett
                    cx = detl + w/2
                    cy = dett + h/2
                    d = float(np.median(depth[ cy - h/6 : cy + h/6, cx - w/6 : cx + w/6 ]))
                    conv = rs.convert(cx,cy,d)
                    print([cx,cy,d,]+conv)
                    img_rgb_res
                    tracker.start_track(img_bgr_res, dlib.rectangle(detl, dett, detr, detb))
                    track = True
                    if 0:
                        cv2.rectangle(img_rgb_res, (detl, dett), (detr, detb), (0, 0, 255))
                        cv2.imshow("res",img_rgb_res)

            if track:
                tracker.update(color)
                tracking_point = tracker.get_position()
                tracking_point_x1 = tracking_point.left()
                tracking_point_y1 = tracking_point.top()
                tracking_point_x2 = tracking_point.right()
                tracking_point_y2 = tracking_point.bottom()
                w = tracking_point_x2 - tracking_point_x1
                h = tracking_point_y2 - tracking_point_y1
                cx = tracking_point_x1 + w/2
                cy = tracking_point_y1 + h/2
                dArea = depth[ int(cy - h/6) : int(cy + h/6), int(cx - w/6) : int(cx + w/6) ]
                if dArea.shape != (0,0):
                    d = float(np.median(dArea))
                    conv = np.asarray([cx,cy,] + rs.convert(cx,cy,d))
                    if sum(np.isnan(conv))==0:
                        conv = LPF.calc(np.asarray(conv))
                        cx = int(conv[0])
                        cy = int(conv[1])
                        cv2.rectangle(color, (cx-3, cy-3), (cx+3, cy+3), (255, 255, 255), 2)
                        output_x_lpf = conv[2]
                        output_y_lpf = conv[3]
                        output_z_lpf = conv[4]
                        print("pos :",output_x_lpf,output_y_lpf,output_z_lpf)
                tracking_point_x1 = int(tracking_point_x1)
                tracking_point_x2 = int(tracking_point_x2)
                tracking_point_y1 = int(tracking_point_y1)
                tracking_point_y2 = int(tracking_point_y2)
                cv2.rectangle(color, (tracking_point_x1, tracking_point_y1), (tracking_point_x2, tracking_point_y2), (255, 255, 255), 2)

            cv2.imshow("color",color)

            if 0:
                for i in range(len(ret)):
                    msg = OSC.OSCMessage() 
                    msg.setAddress("/human")
                    msg.append(i)
                    msg.append(ret[i][3])
                    msg.append(ret[i][4])
                    msg.append(ret[i][5])
                    osc.send(msg)
        cv2.imshow("test",np.zeros((10,10),dtype="uint8"))
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
    p1.join()
    print("process finish")

if __name__ == "__main__":
    argvs=sys.argv
    print(argvs)
    main(argvs)
