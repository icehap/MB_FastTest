#!/usr/bin/env python3

from iceboot.iceboot_session import getParser, startIcebootSession
from iceboot.test_waveform import parseTestWaveform
from optparse import OptionParser
import numpy as np
import tables
import matplotlib.pyplot as plt
import time
import sys
import signal
from addparser_iceboot import AddParser


def main(parser, inchannel=-1, dacvalue=-1, path='.', feplsr=0):
    (options, args) = parser.parse_args()

    session = startIcebootSession(parser)

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
    plt.xlabel("Waveform Bin")
    plt.ylabel("ADC Count")
    line = None

    if feplsr > 0:
        session.setDAC(setchannel,30000)
        if int(nSamples) > 128:
            session.setDEggConstReadout(channel, 4, int(nSamples))
        session.setDAC('D',feplsr)
        time.sleep(0.1)
        session.enableFEPulser(channel,4)

    if options.external:
        print("external")
        session.startDEggExternalTrigStream(channel)
        print("external")
    elif feplsr > 0: 
        session.startDEggThreshTrigStream(channel,7950)
    elif options.threshold is None:
        session.startDEggSWTrigStream(channel, 
            int(options.swTrigDelay))
    else:
        session.startDEggThreshTrigStream(channel,
            int(options.threshold))

    # define signal handler to end the stream on CTRL-C
    def signal_handler(*args):
        print('\nEnding waveform stream...')
        session.endStream()
        session.disableFEPulser(channel)
        print('Done')
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    i = 0
    while (True):
        if i%100 == 0:
            print('Event#{0}:'.format(i))

        try:
            readout = parseTestWaveform(session.readWFMFromStream())
        except IOError:
            print('Timeout! Ending waveform stream and exiting')
            session.endStream()
            break

        # Check for timeout
        if readout is None:
            continue
        wf = readout["waveform"]
        # Fix for 0x6a firmware
        if len(wf) != nSamples:
            continue
        xdata = [x for x in range(len(wf))]

        if dacvalue > -1:
            filename = path + '/' + str(options.mbsnum) + '/dacscan_ch' + str(channel) + '_' + str(dacvalue) + '.hdf5'
        elif feplsr > 0:
            filename = path + '/' + str(options.mbsnum) + '/plscalib_ch' + str(channel) + '_' + str(feplsr) + '.hdf5'
        elif options.filename is None:
            raise ValueError('Please supply a filename to '
                             'save the data to!')
        else:
            filename = options.filename

        # Prepare hdf5 file
        if i == 0:
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
            plt.axis([0, len(wf),
                      max(wf) - wfrange * 1.2, min(wf) + wfrange * 1.2])
        else:
            plt.axis([0, len(wf), int(options.adcMin),
                      int(options.adcMin) + int(options.adcRange)])
        fig.canvas.draw()
        #if i < 100:
        #    plt.savefig(f'figs/waveform_example_{i}.pdf')
        fig.canvas.flush_events()
        #plt.pause(0.001)
        time.sleep(0.001)

        if i >= int(options.nevents):
            print("Reached end of run - exiting...")
            session.endStream()
            session.disableFEPulser(channel)
            print('Done')
            break
        
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    plt.close()
    return 


if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser,-1,-1,'.')
    sys.exit(0)
