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
    (options, args) = parser.parse_args()
    path = pathSetting(options,'ROFailRate',True)

    session = startIcebootSession(parser)
    loadfw = flashFPGA(session)
    if loadfw == 1:
        sys.exit()

    readouts = []
    intervals = []
    def signal_handler(*args):
        print('\nEnding waveform stream...')
        session.endStream()
        print('Done')
        session.disableHV(int(options.channel))
        np.save(f'{path}/readouts.npy',np.array(readouts))
        np.save(f'{path}/intervals.npy',np.array(intervals))
        sys.exit(0)
    signal.signal(signal.SIGINT,signal_handler)
    
    mode = beginWaveformStream(session,options)
    interval = 0
    while(True):
        print('\rEvent: %d' % interval,end='')
        readout = []
        try:
            if options.block:
                readout = session.readWFBlock()
            else:
                readout = [parseTestWaveform(session.readWFMFromStream())]
        except IOError:
            print('Timeout! Ending waveform stream and re-flasing the FPGA.')
            session.endStream()
            intervals.append(interval)
            interval = 0
            loadfw = flashFPGA(session)
            if loadfw == 1:
                break
            mode = beginWaveformStream(session,options)
            continue

        wfs = []
        for data in readout:
            if data is None:
                continue
            wf = data['waveform']
            wfs.append(wfs)

        readouts.append(wfs)
        interval += 1

    np.save(f'{path}/readouts.npy',np.array(readouts))
    np.save(f'{path}/intervals.npy',np.array(intervals))

    return

if __name__=='__main__':
    parser = getParser()
    AddParser(parser)
    main(parser)
