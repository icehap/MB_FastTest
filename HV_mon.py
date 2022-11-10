#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
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
    path = pathSetting(options,'HVMON',True)

    loadFPGA(parser)

    session = startIcebootSession(parser)
    time.sleep(1)

    channel = int(options.channel)
    session.enableHV(channel)

    hvv  = []
    hvi  = []
    setv = []
    temp = []
    HVstart = 700
    HVend   = 1500
    waittime = 200
    HVstartDelay = int(HVstart/50)
    stages = np.linspace(HVstart,HVend,20)

    pbar = tqdm(total = len(stages))
    i = 0
    while i < len(stages):
        stage = stages[i]
        try: 
            session.setDEggHV(channel,int(stage))
        except:
            i = 0
            hvv = []
            hvi = []
            setv = []
            temp = []
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
            time.sleep(0.1)
        i += 1
        pbar.update(1)
    pbar.close()

    store_hdf(f'{path}/data.hdf',hvv,hvi,temp)
    session.setDEggHV(channel,0)
    session.close()

    fig = plt.figure(figsize=(9.6,6.4))
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()
    for i in range(len(stages)):
        ax1.axvline(HVstartDelay*10+10+waittime*i,ls=':',color='magenta',alpha=0.7)
    ax1.plot(np.arange(len(hvv)), hvv, label='Voltage',color='tab:blue')
    ax2.plot(np.arange(len(hvv)), hvi, label='Current',color='tab:orange')
    ax1.set_xlabel('Readout number')
    ax1.set_ylabel('Observed Voltage [V]')
    ax2.set_ylabel('Observed Current [$\mu$A]')

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1+h2,l1+l2)
    plt.tight_layout()
    plt.savefig(f'{path}/hv_relation_time.pdf')
    if options.b:
        plt.show()
    else:
        plt.draw()


def store_hdf(filename, data_hvv, data_hvi, data_temp):
    if not os.path.isfile(filename):
        class Event(tables.IsDescription):
            hvv = tables.Float32Col(shape=np.asarray(data_hvv).shape)
            hvi = tables.Float32Col(shape=np.asarray(data_hvi).shape)
            temp = tables.Float32Col(shape=np.asarray(data_temp).shape)
        with tables.open_file(filename,'w') as f:
            table = f.create_table('/','data',Event)

    with tables.open_file(filename, 'a') as f:
        table = f.get_node('/data')

        event = table.row
        event['hvv'] = data_hvv
        event['hvi'] = data_hvi
        event['temp'] = data_temp
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
