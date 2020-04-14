#!/usr/bin/env python3

from iceboot.iceboot_session import getParser
import os
import sys
import numpy as np
import scope
import tables
import time
from addparser_iceboot import AddParser
import matplotlib.pyplot as plt
from mkplot import plotSetting
from pulserCalib import getThreshold, getData

def main(parser):
    (options, args) = parser.parse_args()

    MBserialnumber = options.mbsnum
    if len(MBserialnumber.split('/')) > 1:
        print('Do not use "/" in the MB serial number. Exit.') 
        sys.exit(0)

    unixtime = int(time.time())
    index = 0 
    prepath = 'results/SH_' + str(MBserialnumber) + '_' + str(unixtime) + '_'
    path = prepath + str(index)

    while os.path.isdir(path):
        index = index + 1
        path = prepath + str(index)

    print(f'=== File path is: {path}. ===')
    os.system('mkdir -p ' + path)

    thresSpeCurve(parser, path)

def thresSpeCurve(parser, path='.'):
    (options, args) = parser.parse_args()

    snum = options.mbsnum
    threshold = options.threshold

    if options.filename is None: 
        print ('Requires option: --filename.')
        print ('Quit.')
        return

    datapath = path + '/' + snum

    os.system('mkdir -p ' + datapath)

    channel = int(options.channel)

    if channel < 0 or channel > 1: 
        return

    threshold = getThreshold(parser, channel, 30000, 20, path)
    scope.main(parser,channel,-1,path,-1,threshold)

    getSpeCurve(parser, channel, datapath)

    return

def getSpeCurve(parser, channel, path): 
    (options, args) = parser.parse_args()
    filename = options.filename

    plotSetting(plt)

    plt.ion()
    plt.show()

    fig = plt.figure()
    plt.xlabel("Integrated Charge [LSB]", ha='right', x=1.0)
    plt.ylabel("Entry",ha='right', y=1.0)

    datapath = path + '/' + filename

    charges = getIntCharges(datapath)

    plt.hist(charges, bins= 400, range=(-100, 300), color='blue', histtype="step", align="left")

    fig.canvas.draw()
    plt.pause(0.001)
    plt.savefig(path+'/hist.pdf')

    return

def getIntCharges(filename): 
    f = tables.open_file(filename)

    data = f.get_node('/data')
    event_ids = data.col('event_id')
    times = data.col('time')
    waveforms = data.col('waveform')

    nsamples = len(waveforms[0])

    charges = []

    for i in range(len(waveforms)): 
        waveform = waveforms[i]
        baseline = np.mean(waveform[0:120])
        subtWf = waveform - baseline
        charge = sum(subtWf[125:135])
        charges.append(charge)

    return charges  

if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)

    main(parser)
