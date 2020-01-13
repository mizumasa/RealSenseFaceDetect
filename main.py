#!/usr/bin/env python
# -*- coding: utf-8 -*-
#auther: mizumasa

import sys
import time
import cv2
import numpy as np
import realsense_face_detect as rs
import osc_of
import OSC

CAM_ON = True

def main(args):
    if CAM_ON:
        cam = rs.RS_FACE()
    demo = False
    if "demo" in args:
        demo = True
    osc = osc_of.PyModule(demo)
    #osc.setup()
    count = 0
    while 1:
        ret = None
        if CAM_ON:
            ret = cam.read()

            for i in range(len(ret)):
                msg = OSC.OSCMessage() 
                msg.setAddress("/human")
                msg.append(i)
                msg.append(ret[i][3])
                msg.append(ret[i][4])
                msg.append(ret[i][5])
                osc.send(msg)

        else:
            cv2.imshow("test",np.zeros((10,10),dtype="uint8"))
        print(ret)
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        
        try:
            msg = OSC.OSCMessage() 
            msg.setAddress("/status")
            msg.append("loop")
            osc.send(msg)
        except:
            print("osc error")
        print(osc.getData())
        count += 1
        #if count > 100:
        #    break

    print("finish")
    osc.close()
    if CAM_ON:cam.close()
    time.sleep(2)
    return

if __name__ == '__main__':
    args = sys.argv
    main(args)


