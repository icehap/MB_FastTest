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

    MBsnum = options.mbsnum
    if len(MBsnum.split('/')) > 1:
        print('Do not use "/" in the MB serial number. Exit.') 
        sys.exit(0)

    unixtime = int(time.time())
    index = 0 
    prepath = f'results/SH_{MBsnum}_{unixtime}_'
    path = prepath + str(index)

    while os.path.isdir(path):
        index = index + 1
        path = prepath + str(index)

    print(f'=== File path is: {path}. ===')
    os.system(f'mkdir -p {path}')

    thresSpeCurve(parser, path)

def thresSpeCurve(parser, path='.'):
    (options, args) = parser.parse_args()

    snum = options.mbsnum
    threshold = options.threshold

    if options.filename is None: 
        print ('Requires option: --filename.')
        print ('Quit.')
        return

    datapath = f'{path}/{snum}'

    os.system(f'mkdir -p {datapath}')

    channel = int(options.channel)

    if channel < 0 or channel > 1: 
        return

    baseline = 0
    baseline = getThreshold(parser, channel, 30000, 0, path)
    print(f'Threshold: {baseline}')
    scope.main(parser,channel,path=path,threshold=12000)

    getSpeCurve(parser, channel, datapath, baseline)

    return

def getSpeCurve(parser, channel, path, baseline): 
    (options, args) = parser.parse_args()
    filename = options.filename

    plotSetting(plt)

    plt.ion()
    plt.show()

    fig = plt.figure()
    plt.xlabel("Integrated Charge [LSB]", ha='right', x=1.0)
    plt.ylabel("Entry",ha='right', y=1.0)

    datapath = f'{path}/{filename}'

    charges, avgwf = getIntCharges(datapath, baseline)

    plt.hist(charges, bins= 800, range=(-200, 600), color='blue', histtype="step", align="left")

    fig.canvas.draw()
    plt.savefig(f'{path}/hist.pdf')

    plt.ylim(0,50)
    fig.canvas.draw()
    plt.savefig(f'{path}/histExpd.pdf')

    fig = plt.figure()
    plt.xlabel("Sampling Bins", ha='right', x=1.0)
    plt.ylabel("ADC counts", ha='right', y=1.0)

    x = np.arange(len(avgwf))
    plt.plot(x, avgwf, color='blue')
    plt.xlim(0,len(avgwf))
    plt.savefig(f'{path}/avgwf.pdf')

    return

def getIntCharges(filename, baseline): 
    f = tables.open_file(filename)

    data = f.get_node('/data')
    event_ids = data.col('event_id')
    times = data.col('time')
    waveforms = data.col('waveform')

    nsamples = len(waveforms[0])

    charges = []

    for i in range(len(waveforms)): 
        waveform = waveforms[i]
        subtWf = waveform - baseline
        charge = sum(subtWf[190:210])
        charges.append(charge)

    avgwf = np.mean(waveforms, axis=0)

    return charges, avgwf  

if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)

    main(parser)
