## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2015-2017 Intel Corporation. All Rights Reserved.

###############################################
##      Open CV and Numpy integration        ##
###############################################

import pyrealsense2 as rs
import numpy as np
import cv2
import dlib
import math

#D415 D = 69.4 x 42.5 x 77
CAM_W = 1280
CAM_H = 720

CAM_ANGLE_W = 69.4 / 2
CAM_ANGLE_H = 42.5 / 2
CAM_ANGLE = 0

CAM_D_W = CAM_W / 2 / math.tan(math.pi * CAM_ANGLE_W / 180)
CAM_D_H = CAM_H / 2 / math.tan(math.pi * CAM_ANGLE_H / 180)
print(CAM_D_W,CAM_D_H)

def convert(cx,cy,cd):
    angle_w = math.atan2(cx - CAM_W/2,CAM_D_W)
    angle_h = CAM_ANGLE - math.atan2(cy - CAM_H/2,CAM_D_H)
    x = cd * math.sin(angle_w)
    y = cd * math.cos(angle_w) * math.sin(angle_h)
    d = cd * math.cos(angle_w) * math.cos(angle_h)
    return [x,y,d]

class RS_FACE():
    def __init__(self,dlib = True):
        # Configure depth and color streams
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.depth, CAM_W, CAM_H, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, CAM_W, CAM_H, rs.format.bgr8, 30)

        # Start streaming
        self.pipeline.start(self.config)
        self.dlibOn = dlib
        if self.dlibOn:
            self.detector = dlib.get_frontal_face_detector()
        return

    def read(self):
        out = []
        frames = self.pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            return None

        # Convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        if not self.dlibOn:
            return color_image, depth_image
        img_rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        
        dets, scores, idx = self.detector.run(img_rgb, 0)
        for det in dets:
            cv2.rectangle(color_image, (det.left(), det.top()), (det.right(), det.bottom()), (0, 0, 255))
            cv2.rectangle(depth_colormap, (det.left(), det.top()), (det.right(), det.bottom()), (0, 0, 255))
            w = det.right() - det.left()
            h = det.bottom() - det.top()
            if w > 20 and h > 20:
                cx = det.left() + w/2
                cy = det.top() + h/2
                d = float(np.median(depth_image[ cy - h/6 : cy + h/6, cx - w/6 : cx + w/6 ]))
                conv = convert(cx,cy,d)
                out.append([cx,cy,d,]+conv)
        # Apply colormap on depth image (image must be converted to 8-bit per pixel first)

        # Stack both images horizontally
        images = np.hstack((color_image, depth_colormap))
        images = cv2.resize(images,(CAM_W,CAM_H/2))
        # Show images
        cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('RealSense', images)
        #cv2.waitKey(1)
        return out

    def close(self):
        self.pipeline.stop()



