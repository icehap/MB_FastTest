#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
import os, sys, time
import datetime
import tables
from testLED import doLEDflashing, setLEDon, disableLEDflashing
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import utils
import shared_options
import traceback
from pulserCalib import getThreshold

def main():
    start_time = time.time()
    parser = getParser()
    shared_options.General(parser)
    shared_options.LED(parser)
    shared_options.Waveform(parser)

    utils.plot_setting(parser)

    (options, args) = parser.parse_args()
    print(options)
    if options.hvv is not None:
        chargestamp_multiple(parser)
    end_time = time.time()
    print(f'Duration: {end_time - start_time:.1f} sec')

def chargestamp_multiple(parser):
    (options, args) = parser.parse_args()
    channel = int(options.channel)

    path = utils.pathSetting(options,'QSTAMP2')
    hdfout = f'{path}/data.hdf'

    set_voltages = [int(i) for i in str(options.hvv).split(',')]

    if options.led:
        session = startIcebootSession(parser)
        session.setDEggExtTrigSourceICM()
        session.startDEggExternalTrigStream(channel)
        doLEDflashing(session, freq=options.freq, bias=options.intensity,flashermask=setLEDon(1))
    else:
        os.makedirs(f'{path}/raw',exist_ok=True)
        threshold = getThreshold(parser, channel, 30000, 9, path)
        session = startIcebootSession(parser)
        session.startDEggThreshTrigStream(channel,)

    time.sleep(1)
    session.enableHV(channel)

    pdf = PdfPages(f'{path}/charge_histograms.pdf')

    i = 0
    prev_setv = 0
    while i < len(set_voltages):
        time.sleep(1)
        setv = set_voltages[i]
        print(f'Set voltage: {setv} V')
        session.setDEggHV(channel,int(setv))
        for j in tqdm(range(int(abs(setv-prev_setv)/50+1))):
            time.sleep(1)
        try:
            datadic = charge_readout(session, options, int(setv), hdfout)
        except:
            traceback.print_exc()
            session.close()
            time.sleep(1)
            session = startIcebootSession(parser)
            time.sleep(1)
            session.enableHV(channel)
            continue
        simple_plot_qhist(pdf, datadic)
        prev_setv = setv
        i += 1

    if options.led:
        disableLEDflashing(session)
    session.disableHV(channel)
    session.close()
    pdf.close()
    return 

def charge_readout(session, options, setHV, filename):
    datadic = dict_init()
    datadic['hvv'] = session.readSloADC_HVS_Voltage(options.channel)
    datadic['hvi'] = session.readSloADC_HVS_Current(options.channel)
    datadic['setv'] = setHV
    datadic['temp'] = session.readSloADCTemperature()

    if options.led:
        block = session.DEggReadChargeBlockFixed(140,155,14*options.nevents,timeout=options.timeout)
    else: 
        block = session.DEggReadChargeBlock(10,15,14*options.nevents,timeout=options.timeout)
    datadic['charge'] = [(rec.charge*1e12) for rec in block[options.channel] if not rec.flags]
    datadic['timestamp'] = [rec.timeStamp for rec in block[options.channel] if not rec.flags]
    print(np.mean(datadic['charge']))
    store_hdf(filename, datadic)
    return datadic

def dict_init():
    return {'hvv':0,'hvi':0,'setv':0,'temp':0,'charge':[0],'timestamp':[0]}

def store_hdf(filename, datadic):
    if not os.path.isfile(filename):
        class Event(tables.IsDescription):
            hvv = tables.Float32Col()
            hvi = tables.Float32Col()
            setv = tables.Int32Col()
            temp = tables.Float32Col()
            timestamp = tables.Int32Col(shape=np.asarray(datadic['timestamp']).shape)
            charge = tables.Float32Col(shape=np.asarray(datadic['charge']).shape)
        with tables.open_file(filename,'w') as f:
            table = f.create_table('/','data',Event)
    with tables.open_file(filename,'a') as f:
        table = f.get_node('/data')
        event = table.row
        for key in datadic:
            event[key] = datadic[key]
        event.append()
        table.flush()

def simple_plot_qhist(pdf, datadic):
    plt.hist(datadic['charge'],bins=500,range=(-2,8),histtype='step')
    plt.xlabel('Charge [pC]')
    plt.ylabel('Entry')
    plt.yscale('log')
    plt.title(f'{datadic["setv"]}V')
    pdf.savefig()
    plt.clf()

if __name__ == '__main__':
    main()
