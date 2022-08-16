#!/usr/bin/env python3

from iceboot.iceboot_session import getParser, startIcebootSession
from iceboot.test_waveform import parseTestWaveform, applyPatternSubtraction
from optparse import OptionParser
from sensorcheck import readSloAdcChannel
import numpy as np
import tables
import matplotlib.pyplot as plt
import time
import os
import sys
import signal
from addparser_iceboot import AddParser
from loadFPGA import loadFPGA
from testLED import doLEDflashing, disableLEDflashing, setLEDon


def main(parser, inchannel=-1, dacvalue=-1, path='.', feplsr=0, threshold=0, testRun=0):
    (options, args) = parser.parse_args()

    print('Start the session.')
    isLoaded = 0
    while not isLoaded:
        try: 
            session = startIcebootSession(parser)
        except: 
            print("Loading failed. Try again...")
        else: 
            isLoaded = 1

    trial = 0
    while session.fpgaVersion()==65535:
        session.close()
        print('Session closed.')
        loadFPGA(parser)
        trial = trial + 1
        print(f'Re-start the session. Trial {trial}...')
        session = startIcebootSession(parser)
    
    nevents = testRun if testRun > 0 else int(options.nevents)
    channel = inchannel if inchannel>-1 else int(options.channel)
    setchannel = 'B' if channel == 1 else 'A'

    if (len(options.dacSettings) == 0) and (dacvalue > -1): 
        session.setDAC(setchannel,dacvalue)
        time.sleep(0.1)
    
    setdacvalue = 0
    if len(options.dacSettings) > 0: 
        for setting in options.dacSettings:
            setdacvalue = setting[1]
    else: 
        setdacvalue = dacvalue
    
    # Number of samples must be divisible by 4
    nSamples = (int(options.samples) / 4) * 4
    if (nSamples < 16):
        print("Number of samples must be at least 16")
        sys.exit(1)

    session.setDEggConstReadout(channel, 2, int(nSamples))

    plt.ion()
    plt.show()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.xlabel("Waveform Bin",ha='right',x=1.0)
    plt.ylabel("ADC Count",ha='right',y=1.0)
    line = None

    HVobs = 0
    if int(options.hvv) > 0:
        if int(nSamples) > 128:
            session.setDEggConstReadout(channel, 4, int(nSamples))
        session.enableHV(channel)
        session.setDEggHV(channel,int(options.hvv))
        time.sleep(60)
        HVobs = session.readSloADC_HVS_Voltage(channel)
        print(f'Observed HV Supply Voltage for channel {channel}: {HVobs} V.')

    if options.led: 
        doLEDflashing(session,freq=options.freq,bias=options.intensity,flashermask=setLEDon(options.flashermask))
        session.setDEggConstReadout(channel, 1, int(nSamples))
    
    if feplsr > 0:
        session.setDAC(setchannel,30000)
        if int(nSamples) > 128:
            session.setDEggConstReadout(channel, 4, int(nSamples))
        session.setDAC('D',feplsr)
        time.sleep(0.1)
        session.enableFEPulser(channel,4)
    
    mode = beginWFstream(session, options, channel, testRun, threshold, feplsr)

    # define signal handler to end the stream on CTRL-C
    def signal_handler(*args):
        print('\nEnding waveform stream...')
        session.endStream()
        session.disableFEPulser(channel)
        print('Done')
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    odir = f'{path}/raw'
    if dacvalue > -1:
        filename = f'{odir}/dacscan_ch{channel}_{dacvalue}.hdf5'
    elif feplsr > 0:
        filename = f'{odir}/plscalib_ch{channel}_{feplsr}.hdf5'
    elif options.filename is None:
        raise ValueError('Please supply a filename to save the data to!')
    else:
        if not os.path.isdir(odir): 
            os.system(f'mkdir -p {odir}')
        filename = f'{odir}/{options.filename}'

    # Prepare hdf5 file
    if not os.path.isfile(filename):
        class Config(tables.IsDescription): 
            threshold = tables.Int32Col()
            mainboard = tables.StringCol(10)
            triggermode = tables.StringCol(10)
            flashid = tables.StringCol(len(session.flashID()))
            fpgaVersion = tables.Int32Col()
            MCUVersion = tables.Int32Col()
            baselinedac = tables.Int32Col()

        with tables.open_file(filename, 'w') as open_file:
            table = open_file.create_table('/', 'config', Config)
            table = open_file.get_node('/config')
            config = table.row
            config['mainboard'] = str(options.mbsnum)
            config['flashid'] = str(session.flashID())
            config['fpgaVersion'] = session.fpgaVersion()
            config['MCUVersion'] = session.softwareVersion()
            config['triggermode'] = mode 
            config['baselinedac'] = setdacvalue
            config.append()
            table.flush()

    else: 
        print("File already exists! Try again. Exit.") 
        return 

    i = 0
    index = 0
    while (True):
        print('\rEvent: %d' % i,end='')
        try:
            readout = parseTestWaveform(session.readWFMFromStream())
        except IOError:
            print('Timeout! Ending waveform stream and exiting')
            session.endStream()
            index = index + 1
            mode = beginWFstream(session, options, channel, testRun, threshold, feplsr)
            continue

        # Check for timeout
        if readout is None:
            continue
        if options.bsub: 
            applyPatternSubtraction(readout)
        wf = readout["waveform"]
        # Fix for 0x6a firmware
        if len(wf) != nSamples:
            continue
        xdata = [x for x in range(len(wf))]

        timestamp = readout["timestamp"]
        pc_time = time.time()

        tot = readout["thresholdFlags"]
        
        # Write to hdf5 file
        with tables.open_file(filename, 'a') as open_file:
            try: 
                table = open_file.get_node('/data')
            except:
                class Event(tables.IsDescription):
                    event_id = tables.Int32Col()
                    time = tables.Float32Col(shape=np.asarray(xdata).shape)
                    waveform = tables.Float32Col(shape=np.asarray(wf).shape)
                    timestamp = tables.Int64Col()
                    pc_time = tables.Float32Col()
                    thresholdFlags = tables.Int32Col(shape=np.asarray(xdata).shape)
                    temperature = tables.Float32Col()
                    hv = tables.Float32Col()
                    channel = tables.Int32Col()
                    i_1V1  = tables.Float32Col()
                    i_1V35 = tables.Float32Col()
                    i_1V8  = tables.Float32Col()
                    i_2V5  = tables.Float32Col()
                    i_3V3  = tables.Float32Col()
                    v_1V1  = tables.Float32Col()
                    v_1V35 = tables.Float32Col()
                    v_1V8  = tables.Float32Col()
                    v_2V5  = tables.Float32Col()
                    v_3V3  = tables.Float32Col()
                table = open_file.create_table('/', 'data', Event)
                table = open_file.get_node('/data')

            event = table.row
            event['event_id'] = i
            event['time'] = np.asarray(xdata, dtype=np.float32)
            event['waveform'] = np.asarray(wf, dtype=np.float32)
            event['timestamp'] = timestamp 
            event['pc_time'] = pc_time 
            event['thresholdFlags'] = tot
            event['temperature'] = readSloAdcChannel(session,7)
            event['channel'] = channel
            event['hv'] = session.readSloADC_HVS_Voltage(channel)
            event['i_1V1']  = readSloAdcChannel(session,0) 
            event['i_1V35'] = readSloAdcChannel(session,1) 
            event['i_1V8']  = readSloAdcChannel(session,2) 
            event['i_2V5']  = readSloAdcChannel(session,3) 
            event['i_3V3']  = readSloAdcChannel(session,4) 
            event['v_1V1']  = readSloAdcChannel(session,12) 
            event['v_1V35'] = readSloAdcChannel(session,13) 
            event['v_1V8']  = readSloAdcChannel(session,5) 
            event['v_2V5']  = readSloAdcChannel(session,14) 
            event['v_3V3']  = readSloAdcChannel(session,15) 
            event.append()
            table.flush()

        i += 1

        if not line:
            line, = ax.plot(xdata, wf, 'r-')
        else:
            line.set_ydata(wf)
        if (options.adcMin is None or options.adcRange is None):
            wfrange = (max(wf) - min(wf))
            plt.axis([0, len(wf), max(wf) - wfrange * 1.2, min(wf) + wfrange * 1.2])
        else:
            plt.axis([0, len(wf), int(options.adcMin), int(options.adcMin) + int(options.adcRange)])

        if options.b: 
            fig.canvas.draw()
            fig.canvas.flush_events()
            #plt.pause(0.001)
            time.sleep(0.001)

        if i >= nevents:
            print("\nReached end of run - exiting...")
            session.endStream()
            session.disableFEPulser(channel)
            if options.led:
                disableLEDflashing(session)
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
    mode = ""
    if options.external and testRun==0:
        print('Notice: This is external trigger mode.')
        session.startDEggExternalTrigStream(channel)
        mode = "external"
    elif feplsr > 0: 
        print('Notice: This is FE pulser mode.')
        session.startDEggThreshTrigStream(channel,threshold)
        mode = "threshold"
    elif threshold > 0: 
        print(f'Notice: This is threshold trigger mode with threshold:{threshold}.')
        session.startDEggThreshTrigStream(channel,threshold)
        mode = "threshold"
    elif options.threshold is None:
        print('Notice: This is software trigger mode.')
        session.startDEggSWTrigStream(channel, int(options.swTrigDelay))
        mode = "software"
    else:
        print('Notice: This is threshold trigger mode.')
        session.startDEggThreshTrigStream(channel, int(options.threshold))
        mode = "threshold"

    return mode

if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser,-1,-1,'.')
    sys.exit(0)
