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
from pulserCalib import getThreshold


def main(parser): 
    (options, args) = parser.parse_args()
    if options.g:
        print('engine agg')
        import matplotlib as mpl
        mpl.use('Agg')
    elif not options.b:
        print('engine pdf')
        import matplotlib as mpl
        mpl.use('PDF')

    nevents = int(options.nevents)
    path = pathSetting(options,'HVMONQ',True)
    channel = int(options.channel)

    loadFPGA(parser)

    threshold_above_baseline = 10 if (options.bsthres is None) else int(options.bsthres)
    os.system(f'mkdir -p {path}/raw')
    threshold = getThreshold(parser, channel, 30000, threshold_above_baseline, path)
    print(f'threshold is {threshold}')

    session = startIcebootSession(parser)
    time.sleep(1)

    session.enableHV(channel)
    #nSamples = (int(options.samples) / 4) * 4
    #session.setDEggConstReadout(channel, 2, int(nSamples))
    #session.startDEggSWTrigStream(channel, int(options.swTrigDelay))
    session.startDEggThreshTrigStream(channel, threshold) 

    datadict = dict_init()
    HVstart = int(options.vmin)
    HVend   = int(options.vmax)
    waittime = int(options.wtime)
    waittimelong = int(options.wtimelong)
    HVstartDelay = int(HVstart/50)
    up_stages = np.linspace(HVstart,HVend,options.vstep)
    down_stages = np.linspace(HVend,HVstart,options.vstep)
    stages = np.hstack((up_stages,down_stages))

    hdfout = f'{path}/data.hdf'

    hvv = []
    hvi = []
    qmean = []

    pbar = tqdm(total = len(stages))
    i = 0
    while i < len(stages):
        stage = stages[i]
        isException = 0
        try: 
            session.setDEggHV(channel,int(stage))
        except:
            i = 0
            datadict = dict_init()
            pbar.reset()
            session.close()
            time.sleep(1)
            session = startIcebootSession(parser)
            time.sleep(1)
            session.enableHV(channel)
            session.startDEggThreshTrigStream(channel, threshold) 
            continue

        if i==0:
            readout_length = HVstartDelay*10+waittime
        else:
            readout_length = waittime

        this_hvi = []
        for iteration in tqdm(np.arange(readout_length),leave=False):
            try:
                datadict = charge_readout(session, channel, stage, nevents, hdfout)
            except Exception:
                isException = 1
                i = 0 
                pbar.reset()
                break
            this_hvi.append(datadict['hvi'])
            hvv.append(datadict['hvv'])
            hvi.append(datadict['hvi'])
            qmean.append(np.mean(np.array(datadict['charge'])))
        if isException:
            continue
        # long term monitoring
        if (i!=0) and (np.std(this_hvi)>1):
            for iteration in tqdm(np.arange(waittimelong),leave=False):
                try:
                    datadict = charge_readout(session, channel, stage, nevents, hdfout)
                except Exception:
                    isException = 1
                    i = 0
                    pbar.reset()
                    break
                hvv.append(datadict['hvv'])
                hvi.append(datadict['hvi'])
                qmean.append(np.mean(np.array(datadict['charge'])))
            if isException:
                continue
        i += 1
        pbar.update(1)
    pbar.close()

    session.setDEggHV(channel,0)
    session.close()

    hvi_std = [np.std(hvi[10*i:10*(i+1)]) for i in range(int(len(hvi)/10))]

    # Voltage, Current 
    fig = plt.figure(figsize=(11.2,6.4))
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()
    #ax3 = ax1.twinx()
    
    fig.suptitle(f'{options.mbsnum} Ch-{channel}')
    ax1.plot(np.arange(len(hvv)), hvv, label='Voltage',color='tab:blue')
    ax2.plot(np.arange(len(hvv)), hvi, label='Current',color='tab:orange')
    ax2.plot(np.arange(len(hvi_std))*10, hvi_std, label='Current RMS', color='tab:red')
    ax1.set_xlabel('Readout number')
    ax1.set_ylabel('Observed Voltage [V]')
    ax2.set_ylabel('Observed Current [$\mu$A]')
    #ax3.set_ylabel('$\sigma_{I_\mathrm{obs}}$ [%]')
    #ax3.spines['right'].set_position(('axes',1.1))

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    #h3, l3 = ax3.get_legend_handles_labels()
    ax1.legend(h1+h2,l1+l2)
    #ax1.legend(h1+h2+h3,l1+l2+l3)
    ax1.set_ylim(0,2000)
    ax2.set_ylim(0,20)
    #ax3.set_ylim(0,16)
    plt.tight_layout(rect=[0,0,1,0.97])
    plt.savefig(f'{path}/hv_relation_time.pdf')
    if not options.b:
        plt.show()
    else:
        plt.draw()

    # Mean Charge with the data-taking threshold of +9
    figure = plt.figure(figsize=(11.2,6.4))
    plt.plot(np.arange(len(qmean)),qmean,label='Mean Charge')
    plt.xlabel('Readout number')
    plt.ylabel('Charge [pC]')
    plt.tight_layout()
    plt.savefig(f'{path}/mean-charge.pdf')
    if not options.b:
        plt.show()
    else:
        plt.draw()

def charge_readout(session, channel, stage, nevents, filename):
    datadict = dict_init()
    datadict['hvv'] = getHVV(session,channel)
    datadict['hvi'] = getHVI(session,channel)
    datadict['setv'] = stage
    datadict['temp'] = getTemp(session)
    try: 
        block = session.DEggReadChargeBlock(10,15,14*nevents,timeout=10)
    except IOError:
        session.endStream()
        session.close()
        time.sleep(1)
        session = startIcebootSession(parser)
        time.sleep(1)
        session.enableHV(channel)
        raise Exception('Timeout or Error in the block readout. Restarted...')
    datadict['charge'] = [(rec.charge * 1e12) for rec in block[channel] if not rec.flags]
    datadict['timestamp'] = [rec.timeStamp for rec in block[channel] if not rec.flags]
    store_hdf_array(filename,datadict)
    return datadict


def dict_init():
    return {'hvv': 0,'hvi': 0,'setv': 0,'temp': 0,'charge':[0],'timestamp': [0]}

def store_hdf_array(filename, datadict):
    if not os.path.isfile(filename):
        class Event(tables.IsDescription):
            hvv = tables.Float32Col()
            hvi = tables.Float32Col()
            setv = tables.Int32Col()
            temp = tables.Float32Col()
            timestamp = tables.Int32Col(shape=np.asarray(datadict['timestamp']).shape)
            charge = tables.Float32Col(shape=np.asarray(datadict['charge']).shape)
        with tables.open_file(filename,'w') as f:
            table = f.create_table('/','data',Event)

    with tables.open_file(filename,'a') as f:
        table = f.get_node('/data')
        event = table.row
        for key in datadict:
            event[key] = datadict[key]
        event.append()
        table.flush()

def store_hdf(filename, datadic):
    if not os.path.isfile(filename):
        class Event(tables.IsDescription):
            hvv = tables.Float32Col(shape=np.asarray(datadic['hvv']).shape)
            hvi = tables.Float32Col(shape=np.asarray(datadic['hvi']).shape)
            setv = tables.Int32Col(shape=np.asarray(datadic['setv']).shape)
            temp = tables.Float32Col(shape=np.asarray(datadic['temp']).shape) 
            wf = tables.Float32Col(shape=np.asarray(datadic['charge']).shape)
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
        event['charge'] = datadic['charge']
        event['timestamp'] = datadic['timestamp']
        event.append()
        table.flush()
    
if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)
    parser.add_option("--vmin",type=int,default=700)
    parser.add_option("--vmax",type=int,default=1500)
    parser.add_option("--vstep",type=int,default=21)
    parser.add_option("--wtime",type=int,default=100)
    parser.add_option("--wtimelong",type=int,default=2500)
    parser.add_option("-g",action="store_true",default=False)
    (options, args) = parser.parse_args()

    main(parser)
