#!/usr/bin/env python
# -*- coding: utf-8 -*-

#import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

cutoff_hz = 1.0
dt = 1.0/24

class LowPassFilter():

    def __init__(self):

        self.__dt = 0.0
        self.__g = 0.0

        self.__u_z1 = 0.0
        self.__y_z1 = 0.0

    def set_param(self, init_data, cutoff_hz, dt):

        # 初期値の設定.
        self.__u_z1 = init_data
        self.__y_z1 = init_data
        self.__dt = dt
        self.__g = 2.0 * 3.14 * cutoff_hz

    def calc(self, u):
    
        gT = self.__g * self.__dt
        y = ((2.0-gT)*self.__y_z1 + gT*(u+self.__u_z1))/(2.0+gT)

        self.__u_z1 = u
        self.__y_z1 = y

        return y

if __name__ == "__main__":
    pass





