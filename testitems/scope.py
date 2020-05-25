#!/usr/bin/env python3

from iceboot.iceboot_session import getParser, startIcebootSession
from iceboot.test_waveform import parseTestWaveform
from optparse import OptionParser
import numpy as np
import tables
import matplotlib.pyplot as plt
import time
import os
import sys
import signal
from addparser_iceboot import AddParser
from loadFPGA import loadFPGA


def main(parser, inchannel=-1, dacvalue=-1, path='.', feplsr=0, threshold=0, testRun=0):
    (options, args) = parser.parse_args()

    print('Start the session.')
    session = startIcebootSession(parser)
    trial = 0
    while session.fpgaVersion()==65535:
        session.close()
        print('Session closed.')
        loadFPGA(parser)
        trial = trial + 1
        print (trial)
        print('Re-start the session.')
        session = startIcebootSession(parser)
    
    nevents = int(options.nevents)
    if testRun > 0: 
        nevents = testRun

    channel = 0
    if inchannel>-1: 
        channel = inchannel
    else:
        channel = int(options.channel)

    setchannel = 'A'
    if channel == 1:
        setchannel = 'B'

    if (len(options.dacSettings) == 0) and (dacvalue > -1): 
        session.setDAC(setchannel,dacvalue)
        time.sleep(0.1)
    
    # Number of samples must be divisible by 4
    nSamples = (int(options.samples) / 4) * 4
    if (nSamples < 16):
        print("Number of samples must be at least 16")
        sys.exit(1)

    session.setDEggConstReadout(channel, 1, int(nSamples))

    plt.ion()
    plt.show()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.xlabel("Waveform Bin",ha='right',x=1.0)
    plt.ylabel("ADC Count",ha='right',y=1.0)
    line = None

    if int(options.hvv) > 0:
        if int(nSamples) > 128:
            session.setDEggConstReadout(channel, 4, int(nSamples))
        session.setDEggHV(channel,int(options.hvv))
        session.enableHV(channel)
        time.sleep(1)
        HVobs = session.readSloADC_HVS_Voltage(channel)
        print(f'Observed HV Supply Voltage for channel {channel}: {HVobs} V.')

    if feplsr > 0:
        session.setDAC(setchannel,30000)
        if int(nSamples) > 128:
            session.setDEggConstReadout(channel, 4, int(nSamples))
        session.setDAC('D',feplsr)
        time.sleep(0.1)
        session.enableFEPulser(channel,4)

    if options.external and testRun==0:
        print('Notice: This is external trigger mode.')
        session.startDEggExternalTrigStream(channel)
    elif feplsr > 0: 
        print('Notice: This is FE pulser mode.')
        session.startDEggThreshTrigStream(channel,threshold)
    elif threshold > 0: 
        print(f'Notice: This is threshold trigger mode with threshold:{threshold}.')
        session.startDEggThreshTrigStream(channel,threshold)
    elif options.threshold is None:
        print('Notice: This is software trigger mode.')
        session.startDEggSWTrigStream(channel, int(options.swTrigDelay))
    else:
        print('Notice: This is threshold trigger mode.')
        session.startDEggThreshTrigStream(channel, int(options.threshold))

    # define signal handler to end the stream on CTRL-C
    def signal_handler(*args):
        print('\nEnding waveform stream...')
        session.endStream()
        session.disableFEPulser(channel)
        print('Done')
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    i = 0
    index = 0
    while (True):
        try:
            readout = parseTestWaveform(session.readWFMFromStream())
        except IOError:
            print('Timeout! Ending waveform stream and exiting')
            session.endStream()
            index = index + 1
            beginWFstream(session, options, channel, testRun, threshold, feplsr)
            continue

        # Check for timeout
        if readout is None:
            continue
        wf = readout["waveform"]
        # Fix for 0x6a firmware
        if len(wf) != nSamples:
            continue
        xdata = [x for x in range(len(wf))]

        if dacvalue > -1:
            filename = f'{path}/{options.mbsnum}/dacscan_ch{channel}_{dacvalue}.hdf5'
        elif feplsr > 0:
            filename = f'{path}/{options.mbsnum}/plscalib_ch{channel}_{feplsr}.hdf5'
        elif options.filename is None:
            raise ValueError('Please supply a filename to save the data to!')
        else:
            odir = f'{path}/{options.mbsnum}'
            if not os.path.isdir(odir): 
                os.system(f'mkdir -p {odir}')
            filename = f'{odir}/{options.filename}'

        # Prepare hdf5 file
        #if i == 0:
        if not os.path.isfile(filename):
            class Event(tables.IsDescription):
                event_id = tables.Int32Col()
                time = tables.Float32Col(
                    shape=np.asarray(xdata).shape)
                waveform = tables.Float32Col(
                    shape=np.asarray(wf).shape)

            with tables.open_file(filename, 'w') as open_file:
                table = open_file.create_table('/', 'data', Event)

        # Write to hdf5 file
        with tables.open_file(filename, 'a') as open_file:
            table = open_file.get_node('/data')
            event = table.row

            event['event_id'] = i
            event['time'] = np.asarray(xdata, dtype=np.float32)
            event['waveform'] = np.asarray(wf, dtype=np.float32)
            event.append()
            table.flush()

        i += 1

        # File writing for inhomogenious waveforms (not so efficient)
        '''
        # Write to hdf5 file
        TableLayout = []
        TableLayout.append(('time', type(xdata[0]))
        TableLayout.append(('waveform', type(wf[0]))

        store = np.zeros((1,), dtype=TableLayout)
        store['time'] = xdata
        store['waveform'] = wf

        evt_name = f'event{i}'
        i += 1

        with tables.open_file(filename, 'a') as open_file:
            open_file.create_table('/', evt_name, store)
        '''

        if not line:
            line, = ax.plot(xdata, wf, 'r-')
        else:
            line.set_ydata(wf)
        if (options.adcMin is None or options.adcRange is None):
            wfrange = (max(wf) - min(wf))
            plt.axis([0, len(wf), max(wf) - wfrange * 1.2, min(wf) + wfrange * 1.2])
        else:
            plt.axis([0, len(wf), int(options.adcMin), int(options.adcMin) + int(options.adcRange)])
        fig.canvas.draw()
        fig.canvas.flush_events()
        #plt.pause(0.001)
        time.sleep(0.001)

        if i >= nevents:
            print("Reached end of run - exiting...")
            session.endStream()
            session.disableFEPulser(channel)
            #session.disableHV(channel)
            #session.setDEggHV(channel,0)
            session.close()
            print('Session closed.')
            print('Done')
            time.sleep(1.0)
            break
        
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    plt.close()
    time.sleep(0.5)
    return 

def beginWFstream(session, options, channel, testRun, threshold, feplsr):
    if options.external and testRun==0:
        print('Notice: This is external trigger mode.')
        session.startDEggExternalTrigStream(channel)
    elif feplsr > 0: 
        print('Notice: This is FE pulser mode.')
        session.startDEggThreshTrigStream(channel,threshold)
    elif threshold > 0: 
        print(f'Notice: This is threshold trigger mode with threshold:{threshold}.')
        session.startDEggThreshTrigStream(channel,threshold)
    elif options.threshold is None:
        print('Notice: This is software trigger mode.')
        session.startDEggSWTrigStream(channel, int(options.swTrigDelay))
    else:
        print('Notice: This is threshold trigger mode.')
        session.startDEggThreshTrigStream(channel, int(options.threshold))

if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser,-1,-1,'.')
    sys.exit(0)
