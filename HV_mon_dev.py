#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
from iceboot.test_waveform import parseTestWaveform, applyPatternSubtraction
import os, sys
import numpy as np
import scope 
import time 
from addparser_iceboot import AddParser 
import matplotlib.pyplot as plt 
from sensorcheck import getHVV, getHVI, getTemp
from loadFPGA import loadFPGA
from utils import pathSetting
import tables
from tqdm import tqdm


def main(parser): 
    (options, args) = parser.parse_args()

    nevents = int(options.nevents)
    path = pathSetting(options,'HVMONDEV',True)

    loadFPGA(parser)

    session = startIcebootSession(parser)
    time.sleep(1)

    channel = int(options.channel)
    session.enableHV(channel)
    nSamples = (int(options.samples) / 4) * 4
    session.setDEggConstReadout(channel, 2, int(nSamples))
    session.startDEggSWTrigStream(channel, int(options.swTrigDelay))

    hvv  = []
    hvi  = []
    setv = []
    temp = []
    wf = []
    rms = []
    timestamp = []
    HVstart = 700
    HVend   = 1500
    waittime = 100
    HVstartDelay = int(HVstart/50)
    stages = np.linspace(HVstart,HVend,20)

    pbar = tqdm(total = len(stages))
    i = 0
    while i < len(stages):
        stage = stages[i]
        isException = 0
        try: 
            session.setDEggHV(channel,int(stage))
        except:
            i = 0
            hvv = []
            hvi = []
            setv = []
            temp = []
            wf = []
            rms = []
            timestamp = []
            pbar.reset()
            session.close()
            time.sleep(1)
            session = startIcebootSession(parser)
            time.sleep(1)
            session.enableHV(channel)
            continue

        for iteration in tqdm(np.arange(HVstartDelay*10+waittime if stage==HVstart else waittime),leave=False):
            hvv.append(getHVV(session,channel))
            hvi.append(getHVI(session,channel))
            setv.append(stage)
            temp.append(getTemp(session))
            for j in range(int(options.nevents)):
                try: 
                    readout = parseTestWaveform(session.readWFMFromStream())
                except IOError:
                    isException = 1
                if readout is None:
                    isException = 1
                if isException == 1:
                    print('Timeout or Error. Restarting...')
                    session.endStream()
                    i = 0 
                    hvv = []
                    hvi = []
                    setv = []
                    temp = []
                    wf = []
                    rms = []
                    timestamp = []
                    pbar.reset()
                    session.close()
                    time.sleep(1)
                    session = startIcebootSession(parser)
                    time.sleep(1)
                    session.enableHV(channel)
                    break
                wf.append(readout['waveform'])
                rms.append(np.std(readout['waveform']))
                timestamp.append(readout['timestamp'])
            if isException:
                break
            #time.sleep(0.1-nSamples/240e6*float(options.nevents))
        if isException:
            continue
        i += 1
        pbar.update(1)
    pbar.close()
    
    session.setDEggHV(channel,0)
    session.close()

    fig = plt.figure(figsize=(11.2,6.4))
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    for i in range(len(stages)):
        ax1.axvline(HVstartDelay*10+10+waittime*i,ls=':',color='magenta',lw=1,alpha=0.7)
    ax1.plot(np.arange(len(hvv)), hvv, label='Voltage',color='tab:blue')
    ax2.plot(np.arange(len(hvv)), hvi, label='Current',color='tab:orange')
    ax3.plot(np.arange(len(rms))/int(options.nevents), rms, label='Waveform RMS',color='tab:green')
    ax1.set_xlabel('Readout number')
    ax1.set_ylabel('Observed Voltage [V]')
    ax2.set_ylabel('Observed Current [$\mu$A]')
    ax3.set_ylabel('Waveform RMS [LSB]')
    ax3.spines['right'].set_position(('axes',1.1))

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    h3, l3 = ax3.get_legend_handles_labels()
    ax1.legend(h1+h2+h3,l1+l2+l3)
    ax1.set_ylim(0,1600)
    ax2.set_ylim(0,16)
    ax3.set_ylim(0,16)
    plt.tight_layout()
    plt.savefig(f'{path}/hv_relation_time.pdf')
    if options.b:
        plt.show()
    else:
        plt.draw()
    datadic = {'hvv': hvv, 'hvi': hvi, 'setv': stages, 'temp': temp, 'wf': wf, 'rms': rms, 'timestamp': timestamp}
    store_hdf(f'{path}/data.hdf',datadic)


def store_hdf(filename, datadic):
    if not os.path.isfile(filename):
        class Event(tables.IsDescription):
            hvv = tables.Float32Col(shape=np.asarray(datadic['hvv']).shape)
            hvi = tables.Float32Col(shape=np.asarray(datadic['hvi']).shape)
            setv = tables.Int32Col(shape=np.asarray(datadic['setv']).shape)
            temp = tables.Float32Col(shape=np.asarray(datadic['temp']).shape)
            wf = tables.Int32Col(shape=np.asarray(datadic['wf']).shape)
            timestamp = tables.Int32Col(shape=np.asarray(datadic['timestamp']).shape)
        with tables.open_file(filename,'w') as f:
            table = f.create_table('/','data',Event)

    with tables.open_file(filename, 'a') as f:
        table = f.get_node('/data')

        event = table.row
        event['hvv'] = datadic['hvv']
        event['hvi'] = datadic['hvi']
        event['temp'] = datadic['temp']
        event['setv'] = datadic['setv']
        event['wf'] = datadic['wf']
        event['timestamp'] = datadic['timestamp']
        event.append()
        table.flush()
    
if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)
    (options, args) = parser.parse_args()
    if not options.b:
        import matplotlib as mpl
        mpl.use('PDF')

    main(parser)
