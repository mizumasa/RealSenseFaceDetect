#!/usr/bin/env python
# -*- coding:utf-8 -*-
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
correlation_tracker.py.

Usage:
  correlation_tracker.py [<video source>] [<resize rate>]
'''


import sys
import dlib
import cv2
import time
import copy

# マウスイベントハンドラ
mouse_start_x, mouse_start_y = 0, 0
mouse_end_x, mouse_end_y = 0, 0
selecting = False
tracker_start_flag = False
tracking_flag = False
def select_roi(event,x,y,flags,param):
    global selecting, tracker_start_flag
    global mouse_start_x, mouse_start_y
    global mouse_end_x, mouse_end_y
    if event == cv2.EVENT_LBUTTONDOWN:
        selecting = True
        mouse_start_x, mouse_start_y = x,y

    elif event == cv2.EVENT_MOUSEMOVE:
        if selecting == True:
            mouse_end_x, mouse_end_y = x, y
        else:
            pass
    elif event == cv2.EVENT_LBUTTONUP:
        mouse_end_x, mouse_end_y = x, y
        selecting = False
        tracker_start_flag = True

# 引数解釈
try:
    fn = sys.argv[1]
    if fn.isdigit() == True:
        fn = int(fn)
except:
    fn = 0
try:
    resize_rate = sys.argv[2]
    resize_rate = int(resize_rate)
except:
    resize_rate = 1

# トラッカー生成
tracker = dlib.correlation_tracker()

video_input = cv2.VideoCapture(fn)
if (video_input.isOpened() == True):
    ret, frame = video_input.read()
    cv2.imshow('correlation tracker', frame)
    cv2.setMouseCallback('correlation tracker', select_roi)

while(video_input.isOpened() == True):
    ret, frame = video_input.read()
    temp_frame = copy.deepcopy(frame)

    # 処理負荷軽減のための対象フレーム縮小（引数指定時）
    height, width = frame.shape[:2]
    temp_frame = cv2.resize(frame, (int(width/resize_rate), int(height/resize_rate)))

    if tracker_start_flag == True:
        # 追跡開始
        tracker.start_track(temp_frame, dlib.rectangle(mouse_start_x, mouse_start_y, mouse_end_x, mouse_end_y))
        tracking_flag = True
        tracker_start_flag = False
    elif tracking_flag == True:
        # 追跡更新
        tracker.update(temp_frame)

    # 描画
    if selecting == True:
        cv2.rectangle(frame, (mouse_start_x, mouse_start_y), (mouse_end_x, mouse_end_y), (0, 0, 255), 2)
    if tracking_flag == True:
        tracking_point = tracker.get_position()
        tracking_point_x1 = int(tracking_point.left())
        tracking_point_y1 = int(tracking_point.top())
        tracking_point_x2 = int(tracking_point.right())
        tracking_point_y2 = int(tracking_point.bottom())
        cv2.rectangle(frame, (tracking_point_x1, tracking_point_y1), (tracking_point_x2, tracking_point_y2), (0, 0, 255), 2)

    cv2.imshow('correlation tracker', frame)

    c = cv2.waitKey(50) & 0xFF

    if c==27: # ESC
        break