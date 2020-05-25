#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
import os 
import sys
import numpy as np
import scope 
import tables 
import time 
import glob
from natsort import natsorted
from addparser_iceboot import AddParser 
import matplotlib.pyplot as plt 
import mkplot 
from mkplot import plotSetting
import dacscan
from loadFPGA import loadFPGA

def main(parser): 
    (options, args) = parser.parse_args()

    snum = options.mbsnum 
    if len(snum.split('/')) > 1:
        print('Do not use "/" in the MB serial number. Exit.')
        sys.exit(0)

    unixtime = int(time.time())
    index = 0 
    prepath = f'results/RL_{snum}_{unixtime}_'
    path = prepath + str(index) 
    while os.path.isdir(path):
        index = index + 1
        path = prepath + str(index)

    repeatCount = 100

    loadFPGA(parser)

    ### copy from dacscan.py... to be optimized
    modes = [1,2,4,8,16,32,64,128,256] # divisors of 64 
    mode = modes[1] + 1
    if int(options.dsmode) < len(modes):
        mode = modes[int(options.dsmode)] + 1

    dacvalue = np.linspace(0,64,mode)
    dacvalue10 = dacvalue * 1000 
    ###
    
    for i in range(repeatCount):
        path_sub = f'{path}/index_{i}'
        print(f'=== File path is: {path_sub}. ===')
        os.system(f'mkdir -p {path_sub}') 

        loadFPGA(parser)
        dacscan.dacscan(parser,path_sub)
        time.sleep(0.1)

    plotSetting(plt)

    plt.ion()
    plt.show()

    colors = ['blue','red']

    xmean0 = []
    ymean0 = []
    yerr0 = []

    xmean1 = []
    ymean1 = []
    yerr1 = []

    for i in range(len(dacvalue10)):
        fig = plt.figure()
        plt.xlabel("RMS Noise [LSB]",ha='right',x=1.0)
        plt.ylabel("Entry",ha='right',y=1.0)
        nevts = 0
        for channel in range(2):
            filenames = glob.glob(f'{path}/index_*/{snum}/dacscan_ch{channel}_{int(dacvalue10[i])}.hdf5')
            x, y, yerr, minFFT, maxFFT = mkplot.mkDataSet(filenames)
            nevts = nevts + len(y)
            if len(y)==0: 
                continue
            plt.hist(y,color=colors[channel],histtype="step",bins=100,range=(0,10),label=f'Ch{channel}')
            if channel==0: 
                xmean0.append(np.mean(x))
                ymean0.append(np.mean(y))
                yerr0.append(np.std(y))
            elif channel==1:
                xmean1.append(np.mean(x))
                ymean1.append(np.mean(y))
                yerr1.append(np.std(y))

        if nevts==0: 
            continue
        plt.xlim(0,10)
        plt.legend()
        plt.savefig(f'{path}/hist_{int(dacvalue10[i])}.pdf')

    fig = plt.figure()
    plt.xlabel("Baseline Mean [LSB]",ha='right',x=1.0)
    plt.ylabel("$\sigma$(RMS noise dist.) [LSB]",ha='right',y=1.0)
    plt.plot(xmean0,yerr0,color=colors[0],label='Ch0',marker="o")
    plt.plot(xmean1,yerr1,color=colors[1],label='Ch1',marker="o")
    plt.legend()
    plt.savefig(f'{path}/Spread.pdf')

    
if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)

    main(parser)
