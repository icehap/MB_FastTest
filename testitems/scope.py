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


def main(parser, dacvalue, path):
    (options, args) = parser.parse_args()

    session = startIcebootSession(parser)

    if (len(options.dacSettings) == 0) and (dacvalue > -1): 
        setchannel = 'A'
        if options.channel == 1 : 
            setchannel = 'B'
        session.setDAC(setchannel,dacvalue)
        time.sleep(0.1)
    
    # Number of samples must be divisible by 4
    nSamples = (int(options.samples) / 4) * 4
    if (nSamples < 16):
        print("Number of samples must be at least 16")
        sys.exit(1)

    session.setDEggConstReadout(int(options.channel), 1, int(nSamples))

    plt.ion()
    plt.show()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.xlabel("Waveform Bin")
    plt.ylabel("ADC Count")
    line = None

    if options.external:
        print("external")
        session.startDEggExternalTrigStream(int(options.channel))
        print("external")
    elif options.threshold is None:
        session.startDEggSWTrigStream(int(options.channel), 
            int(options.swTrigDelay))
    else:
        session.startDEggThreshTrigStream(int(options.channel),
            int(options.threshold))

    # define signal handler to end the stream on CTRL-C
    def signal_handler(*args):
        print('\nEnding waveform stream...')
        session.endStream()
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
            filename = path + str(options.mbsnum) + '/dacscan_ch' + str(options.channel) + '_' + str(dacvalue) + '.hdf5'
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
            print('Done')
            break
        
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    plt.close()
    return 

def AddParser(parser):
    parser.add_option("--mbsnum",dest="mbsnum",
                      help="MB serial number (just for testing)",default="1-001")
    parser.add_option("--channel", dest="channel",
                      help="Waveform ADC channel", default="0")
    parser.add_option("--samples", dest="samples", help="Number of samples "
                               "per waveform",  default=256)
    parser.add_option("--threshold", dest="threshold",
                      help="Apply threshold trigger instead of CPU trigger "
                           "and trigger at this level", default=None)
    parser.add_option("--adcMin", dest="adcMin",
                      help="Minimum ADC value to plot", default=None)
    parser.add_option("--adcRange", dest="adcRange",
                      help="Plot this many ADC counts above min",
                      default=None)
    parser.add_option("--swTrigDelay", dest="swTrigDelay",
                      help="ms delay between software triggers",
                      default=10)
    parser.add_option("--external", dest="external", action="store_true",
                      help="Use external trigger", default=False)
    parser.add_option("--filename", dest="filename", default=None)
    parser.add_option("--timeout", dest="timeout", default=10)
    parser.add_option("--nevents", dest="nevents", default=50000)


if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser,-1,'.')
    sys.exit(0)
