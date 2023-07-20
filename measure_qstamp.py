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
import shutil

def main():
    start_time = time.time()
    parser = getParser()
    shared_options.General(parser)
    shared_options.LED(parser)
    shared_options.Waveform(parser)
    parser.add_option('--analysis',help='do analysis',action='store_true',default=False)
    parser.add_option('--qmax',default=None)

    utils.plot_setting(parser)

    (options, args) = parser.parse_args()
    print(options)
    
    path = utils.pathSetting(options,'QSTAMP2')

    if options.hvv is not None:
        chargestamp_multiple(parser, path, doAnalysis=options.analysis,debug=options.debug)
    end_time = time.time()
    print(f'Duration: {end_time - start_time:.1f} sec')

def chargestamp_multiple(parser, path, channel=None, doAnalysis=False, fillzero=False, hvset=None, nevents=None,debug=False,led_intensity=None,fillnan=False,analysis_startv=None):
    (options, args) = parser.parse_args()

    os.makedirs(f'{path}/raw',exist_ok=True)
    
    if channel is None:
        channel = int(options.channel)
    hdfout = f'{path}/raw/data_ch{channel}.hdf'

    if led_intensity is None:
        led_intensity = options.intensity

    if hvset is not None:
        set_voltages = [int(i) for i in str(hvset).split(',')]
    else:
        set_voltages = [int(i) for i in str(options.hvv).split(',')]

    session = startIcebootSession(parser)
    while session.fpgaVersion()==65535:
        utils.flashFPGA(session)
    if not session.readHVInterlock():
        print("Need to set PMT HV interlock... I'll do it.")
        os.system('python3 ../fh_icm_api/pmt_hv_enable.py')
        print("Done")
        time.sleep(1)

    if len(options.dacSettings) == 0:
        session.setDAC('A', 30000)
        session.setDAC('B', 30000)
        time.sleep(1)

    if options.led:
        if not session.readLIDInterlock():
            os.system('python3 ../fh_icm_api/lid_enable.py')
        session.setDEggConstReadout(channel, 1, 256)
        session.setDEggExtTrigSourceICM()
        session.startDEggExternalTrigStream(channel)
        #session.startDEggExternalHBufTrigStream()
    else:
        threshold = waveform.get_baseline(session, options, path, channel=channel) + 9
        print(f'Threshold for channel {channel}: {threshold}')
        session.startDEggThreshTrigStream(channel,threshold)

    time.sleep(1)
    session.enableHV(channel)

    pdf_file_path = f'{path}/charge_histograms_ch{channel}.pdf'
    if os.path.isfile(pdf_file_path):
        os.makedirs(f'{path}/plots',exist_ok=True)
        oldpath = f'{path}/plots/charge_histograms_ch{channel}'
        index = 1
        while os.path.isfile(f'{oldpath}_{index}.pdf'):
            index += 1
        shutil.move(pdf_file_path,f'{oldpath}_{index}.pdf')
    pdf = PdfPages(pdf_file_path)

    i = 0
    prev_setv = 0
    for i in tqdm(range(len(set_voltages)),desc='Data taking progress'):
        time.sleep(1)
        setv = set_voltages[i]
        led_off(session, options.led)
        #print(f'Set voltage: {setv} V')
        session.setDEggHV(channel,int(setv))
        led_on(session, options.freq, led_intensity, setLEDon(1,False), options.led)
        for j in (pbar := tqdm(range(int(abs(setv-prev_setv)/50+1)*2),leave=False)):
            pbar.set_description(f"Waiting for setv {setv} V")
            time.sleep(0.5)
        try:
            datadic = charge_readout(session, options, channel, int(setv), hdfout, fillzero=fillzero, nevents=nevents, debug=debug, fillnan=fillnan)
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
        if analysis_startv is not None:
            startv = int(analysis_startv)
        else:
            startv = 1300
        from analysis.qstamp_analyze import plot_scaled_charge_histogram_wrapper
        ana = plot_scaled_charge_histogram_wrapper(filepath=path,thzero=0.32,startv=startv,steps=250,channel=channel,qmax=options.qmax,do_gain_fit=options.gainfit)

    return path

def led_on(session, freq, bias, ledsel, ledon, debug=False):
    if ledon:
        doLEDflashing(session, freq, bias, ledsel, debug=debug)
        time.sleep(1)

def led_off(session, ledon):
    if ledon:
        disableLEDflashing(session)

def charge_readout(session, options, channel, setHV, filename, fillzero=False, nevents=None, debug=False, fillnan=False):
    datadic = dict_init()
    niter = 100
    datadic['hvv'] = [session.readSloADC_HVS_Voltage(channel) for i in range(niter)]
    datadic['hvi'] = [session.readSloADC_HVS_Current(channel) for i in range(niter)]
    datadic['setv'] = setHV
    datadic['temp'] = [session.readSloADCTemperature() for i in range(niter)]
    datadic['pctime'] = time.time()

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
    if fillnan:
        if len(datadic['charge']) < nevents:
            lack = [-100 for i in range(nevents-len(datadic['charge']))]
            datadic['charge'].extend(lack)
            datadic['timestamp'].extend(lack)
    if debug:
        #print(f"observed charge: {datadic['charge']}")
        print(f"observed #chargestamps: {len(datadic['charge'])} out of {nevents}")
    store_hdf(filename, datadic)
    return datadic

def dict_init():
    return {'hvv':[0],'hvi':[0],'setv':0,'temp':[0],'charge':[0],'timestamp':[0],'pctime':0}

def store_hdf(filename, datadic):
    if not os.path.isfile(filename):
        class Event(tables.IsDescription):
            hvv = tables.Float32Col(shape=np.asarray(datadic['hvv']).shape)
            hvi = tables.Float32Col(shape=np.asarray(datadic['hvi']).shape)
            setv = tables.Int32Col()
            temp = tables.Float32Col(shape=np.asarray(datadic['temp']).shape)
            timestamp = tables.Int32Col(shape=np.asarray(datadic['timestamp']).shape)
            charge = tables.Float32Col(shape=np.asarray(datadic['charge']).shape)
            pctime = tables.Float32Col()
        with tables.open_file(filename,'w') as f:
            table = f.create_table('/','data',Event)
    with tables.open_file(filename,'a') as f:
        table = f.get_node('/data')
        event = table.row
        for key in datadic:
            event[key] = datadic[key]
        event.append()
        table.flush()

def simple_plot_qhist(pdf, datadic, title=None):
    plt.hist(datadic['charge'],bins=500,range=(-2,8),histtype='step')
    plt.xlabel('Charge [pC]')
    plt.ylabel('Entry')
    plt.yscale('log')
    if title is not None:
        plt.title(title)
    else:
        plt.title(f'{datadic["setv"]}V')
    pdf.savefig()
    plt.clf()

def simple_plot_hvs(setv_array, obsv_array, obsv_error, obsi_array, obsi_error):
    plt.errorbar(setv_array,obsv_array)

if __name__ == '__main__':
    main()
