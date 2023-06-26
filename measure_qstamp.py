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
import waveform
import traceback

def main():
    start_time = time.time()
    parser = getParser()
    shared_options.General(parser)
    shared_options.LED(parser)
    shared_options.Waveform(parser)
    parser.add_option('--analysis',help='do analysis',action='store_true',default=False)

    utils.plot_setting(parser)

    (options, args) = parser.parse_args()
    print(options)
    
    path = utils.pathSetting(options,'QSTAMP2')

    if options.hvv is not None:
        chargestamp_multiple(parser, path, doAnalysis=options.analysis)
    end_time = time.time()
    print(f'Duration: {end_time - start_time:.1f} sec')

def chargestamp_multiple(parser, path, channel=None, doAnalysis=False, fillzero=False, hvset=None, nevents=None):
    (options, args) = parser.parse_args()

    os.makedirs(f'{path}/raw',exist_ok=True)
    
    if channel is None:
        channel = int(options.channel)
        hdfout = f'{path}/raw/data.hdf'
    else:
        hdfout = f'{path}/raw/data_ch{channel}.hdf'

    if hvset is not None:
        set_voltages = [int(i) for i in str(hvset).split(',')]
    else:
        set_voltages = [int(i) for i in str(options.hvv).split(',')]

    session = startIcebootSession(parser)
    while session.fpgaVersion()==65535:
        utils.flashFPGA(session)
    if not session.readHVInterlock:
        os.system('python3 ../fh_icm_api/pmt_hv_enable.py')
        sleep(1)

    if options.led:
        session.setDEggExtTrigSourceICM()
        session.startDEggExternalTrigStream(channel)
    else:
        if len(options.dacSettings) == 0:
            session.setDAC('A', 30000)
            session.setDAC('B', 30000)
        threshold = waveform.get_baseline(session, options, path, channel=channel) + 9
        print(f'Threshold for channel {channel}: {threshold}')
        session.startDEggThreshTrigStream(channel,threshold)

    time.sleep(1)
    session.enableHV(channel)

    pdf = PdfPages(f'{path}/charge_histograms_ch{channel}.pdf')

    i = 0
    prev_setv = 0
    for i in tqdm(range(len(set_voltages)),desc='Data taking progress'):
        time.sleep(1)
        setv = set_voltages[i]
        led_off(session, options.led)
        #print(f'Set voltage: {setv} V')
        session.setDEggHV(channel,int(setv))
        for j in (pbar := tqdm(range(int(abs(setv-prev_setv)/50+1)*2),leave=False)):
            pbar.set_description(f"Waiting for setv {setv} V")
            time.sleep(0.5)
        led_on(session, options.freq, options.intensity, setLEDon(1,False), options.led)
        try:
            datadic = charge_readout(session, options, channel, int(setv), hdfout, fillzero=fillzero, nevents=nevents)
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

    led_off(session, options.led)
    session.endStream()
    session.disableHV(channel)
    session.close()
    pdf.close()

    if doAnalysis:
        from analysis.qstamp_analyze import plot_scaled_charge_histogram_wrapper
        ana = plot_scaled_charge_histogram_wrapper(filepath=path,thzero=0.32,startv=1300,steps=250,channel=channel)

    return path

def led_on(session, freq, bias, ledsel, ledon):
    if ledon:
        doLEDflashing(session, freq, bias, ledsel)

def led_off(session, ledon):
    if ledon:
        disableLEDflashing(session)

def charge_readout(session, options, channel, setHV, filename, fillzero=False, nevents=None):
    datadic = dict_init()
    niter = 100
    datadic['hvv'] = [session.readSloADC_HVS_Voltage(channel) for i in range(niter)]
    datadic['hvi'] = [session.readSloADC_HVS_Current(channel) for i in range(niter)]
    datadic['setv'] = setHV
    datadic['temp'] = [session.readSloADCTemperature() for i in range(niter)]

    if nevents is None:
        nevents = int(options.nevents)
    else:
        nevents = int(nevents)

    if options.led:
        block = session.DEggReadChargeBlockFixed(140,155,14*nevents,timeout=options.timeout)
    else: 
        try:
            block = session.DEggReadChargeBlock(10,15,14*nevents,timeout=options.timeout)
        except:
            if fillzero:
                datadic['charge'] = [0]
                datadic['timestamp'] = [0]
                store_hdf(filename, datadic)
                return datadic
            else:
                raise Exception
    datadic['charge'] = [(rec.charge*1e12) for rec in block[channel] if not rec.flags]
    datadic['timestamp'] = [rec.timeStamp for rec in block[channel] if not rec.flags]
    #print(np.mean(datadic['charge']))
    store_hdf(filename, datadic)
    return datadic

def dict_init():
    return {'hvv':[0],'hvi':[0],'setv':0,'temp':[0],'charge':[0],'timestamp':[0]}

def store_hdf(filename, datadic):
    if not os.path.isfile(filename):
        class Event(tables.IsDescription):
            hvv = tables.Float32Col(shape=np.asarray(datadic['hvv']).shape)
            hvi = tables.Float32Col(shape=np.asarray(datadic['hvi']).shape)
            setv = tables.Int32Col()
            temp = tables.Float32Col(shape=np.asarray(datadic['temp']).shape)
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

def simple_plot_hvs(setv_array, obsv_array, obsv_error, obsi_array, obsi_error):
    plt.errorbar(setv_array,obsv_array)

if __name__ == '__main__':
    main()
