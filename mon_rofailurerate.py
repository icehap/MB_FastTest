#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
from iceboot.test_waveform import parseTestWaveform, applyPatternSubtraction
import os,sys
import numpy as np
import scope 
import tables
import time 
import datetime
import signal
from addparser_iceboot import AddParser
from utils import pathSetting, flashFPGA
from wfreadout import beginWaveformStream

def main(parser):
    parser.add_option("--nowfs",action="store_true",default=False)
    parser.add_option("--grad",action="store_true",default=False)
    (options, args) = parser.parse_args()
    path = pathSetting(options,'ROFailRate',True)

    session = startIcebootSession(parser)
    loadfw = flashFPGA(session)
    if loadfw == 1:
        sys.exit()

    readouts = []
    intervals = []
    interval = 0
    threshold = int(options.threshold)
    currentbaseline = 0
    def signal_handler(*args):
        print('\nEnding waveform stream...')
        session.endStream()
        print('Done')
        session.disableHV(int(options.channel))
        with open(f'{path}/events.txt','a') as f:
            f.write(f'{interval}\n')
        with open(f'{path}/baseline.txt','a') as f:
            f.write(f'{currentbaseline}\n')
        if options.grad:
            with open(f'{path}/setthres.txt','a') as f:
                f.write(f'{threshold}\n')
        if not options.nowfs:
            np.save(f'{path}/readouts.npy',np.array(readouts))
        np.save(f'{path}/intervals.npy',np.array(intervals))
        sys.exit(0)
    signal.signal(signal.SIGINT,signal_handler)
    
    mode = beginWaveformStream(session,options)
    print(f'Threshold setting: {threshold}')
    while(True):
        print('\rEvent: %d' % interval,end='')
        readout = []
        try:
            if options.block:
                readout = session.readWFBlock()
            else:
                readout = [parseTestWaveform(session.readWFMFromStream())]
        except IOError:
            print('\nTimeout! Ending waveform stream and re-flasing the FPGA.')
            print(f'The baseline was {currentbaseline}')
            session.endStream()
            intervals.append(interval)
            with open(f'{path}/events.txt','a') as f:
                f.write(f'{interval}\n')
            with open(f'{path}/baseline.txt','a') as f:
                f.write(f'{currentbaseline}\n')
            interval = 0
            loadfw = flashFPGA(session)
            if loadfw == 1:
                break
            if options.grad:
                with open(f'{path}/setthres.txt','a') as f:
                    f.write(f'{threshold}\n')
                threshold += 1
            mode = beginWaveformStream(session,options,threshold)
            print(f'Threshold setting: {threshold}')
            continue

        for data in readout:
            if data is None:
                continue
            wf = data['waveform']
        currentbaseline = np.mean(wf)

        if not options.nowfs:
            readouts.append(wf)
        interval += 1

    if not options.nowfs:
        np.save(f'{path}/readouts.npy',np.array(readouts))
    np.save(f'{path}/intervals.npy',np.array(intervals))

    return

if __name__=='__main__':
    parser = getParser()
    AddParser(parser)
    main(parser)
