#!/usr/bin/env python3

from iceboot.iceboot_session import getParser, startIcebootSession
import os
import sys
import numpy as np
import scope
import tables
import time
import datetime
from addparser_iceboot import AddParser
import matplotlib.pyplot as plt
from mkplot import plotSetting
from pulserCalib import getThreshold, getData
from tqdm import tqdm

def main(parser):
    (options, args) = parser.parse_args()

    snum = options.mbsnum
    if len(snum.split('/')) > 1:
        print('Do not use "/" in the MB serial number. Exit.')
        sys.exit(0)

    date = datetime.date.today()
    index = 1
    prepath = f'results/ScalerMon/{snum}/{date}/Run'
    path = prepath + str(index)

    while os.path.isdir(path):
        index = index + 1
        path = prepath + str(index)

    print(f'=== File path is: {path}. ===')
    os.system(f'mkdir -p {path}')

    doScaler(parser, path)

def doScaler(parser, path='.'):
    (options, args) = parser.parse_args()

    snum = options.mbsnum

    if options.filename is None:
        print ('Requires option: --filename.')
        print ('Quit.')
        return

    datapath = f'{path}/raw'

    os.system(f'mkdir -p {datapath}')

    channel = int(options.channel)

    if channel < 0 or channel > 1:
        return

    baseline = 0
    threshold = 0

    baselineset = 30000
    if len(options.dacSettings)==2:
        print(options.dacSettings)
        dacSet = options.dacSettings[0]
        baselineset = int(dacSet[1])

    if options.threshold is None:
        baseline = getThreshold(parser, channel, baselineset, 0, path)
        print(f'Observed baseline: {baseline}')
        if options.bsthres is not None:
            if baseline - int(baseline) > 0.5:
                baseline = int(baseline) + 1
            else:
                baseline = int(baseline)
            threshold = int(baseline) + int(options.bsthres)
        else:
            threshold = int(baseline + 14)
    else :
        threshold = int(options.threshold)

    print(f'Set threshold: {threshold}')

    durationUS = 100000
    counts = []
    session = startIcebootSession(parser)
    setchannel = 'A'
    if channel == 1:
        setchannel = 'B'
    session.setDAC(setchannel,baselineset)
    session.setDEggTriggerConditions(channel, threshold)
    session.enableDEggTrigger(channel)
    session.enableScalers(channel,durationUS,24)
    time.sleep(5)
    for i in tqdm(range(int(options.nevents))):
        scaler_count = session.getScalerCount(channel)
        if scaler_count > 100: 
            tqdm.write(f'Iteration {i}: {scaler_count/durationUS*1e6} Hz')
        counts.append(int(scaler_count))
        time.sleep(durationUS/1e6)

    npcounts = np.array(counts)
    np.save(f'{datapath}/{options.filename}',npcounts)

    fig = plt.figure()
    plt.xlabel('Measurement ID')
    plt.ylabel('Rate [Hz]')
    xdata = np.arange(len(npcounts))
    plt.plot(xdata,npcounts/durationUS*1e6,marker='o',ls='')
    plt.savefig(f'{path}/nr_fig_{channel}.pdf')
    plt.show()

    return

if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)

    main(parser)
