#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
import os, sys, time
import datetime
from matplotlib.backends.backend_pdf import PdfPages
from tqdm import tqdm

from measure_qstamp import charge_readout,led_on,led_off,simple_plot_qhist, chargestamp_multiple
from testLED import doLEDflashing, setLEDon, disableLEDflashing
import utils 
import shared_options
import numpy as np
import traceback

def main():
    print(datetime.datetime.now())
    led_int_1 = [int(0x4800) + 2048*i for i in range(8)]
    start_time = time.time()

    parser = getParser()
    shared_options.General(parser)
    shared_options.LED(parser)
    shared_options.Waveform(parser)
    parser.add_option('--deggnum', type=str, default='None')
    parser.add_option('--nevts',default=None)
    parser.add_option('--qmax',type=int,default=16)
    parser.add_option('--basehv0',default=None)
    parser.add_option('--basehv1',default=None)
    parser.add_option('--startv',type=int,default=1300)
    parser.add_option('--ledfor0',default=None)
    parser.add_option('--ledfor1',default=None)
    parser.add_option('--gainfit',action='store_true',default=False)
    parser.add_option('--qmeantarget',default=None)
    parser.add_option('--half',default=None)
    (options,args) = parser.parse_args()
    #print(options,args)
    path = utils.pathSetting(options, 'SPELED', dedicated=f'{options.deggnum}')

    if options.hvv is None:
        #hvv = '1300,1400,1500,1600,1700,1800,1900,1950' ## old setting
        hvv = '1300,1500,1700,1900,1950'
    else:
        hvv = options.hvv

    if options.nevts is not None:
        nevents = float(options.nevts)
    else:
        #nevents = 5e4 ## old setting
        nevents = 3e4

    basehv = [1500,1500]
    if options.basehv0 is not None:
        basehv[0] = int(options.basehv0)
    if options.basehv1 is not None:
        basehv[1] = int(options.basehv1)

    do_led_scan = [options.ledfor0, options.ledfor1]

    target_intensity = [0.16,0.16] # 0.1 p.e.
    if options.qmeantarget is not None:
        target_intensity = [float(options.qmeantarget), float(options.qmeantarget)]
        
    channels = [0,1] 
    if options.half is not None:
        channels = [int(options.half)]
    for ch in channels:
        if do_led_scan[ch] is None:
            qmeans = led_scan(parser,path,ch,led_setting=led_int_1, debug=options.debug, basehv=basehv[ch])
            print(qmeans)
            for i, qmean in enumerate(qmeans):
                if qmean > target_intensity[ch]:
                    break
            if i!=0:
                led_int_2 = [led_int_1[i-1] + 256*j for j in range(9)]
                qmeans_2 = led_scan(parser,path,ch,led_setting=led_int_2,debug=options.debug, basehv=basehv[ch])
                for j, qmean_2 in enumerate(qmeans_2):
                   if qmean_2 > target_intensity[ch]:
                       break
            else:
                led_int_2 = led_int_1
                j = 0
            print(qmeans_2)
            this_intensity = led_int_2[j]
        else:
            this_intensity = int(do_led_scan[ch])
        print(f'LED intensity: {hex(this_intensity)}')
        with open(f'{path}/log.txt','a') as f:
            f.write(f'\nLED intensity for channel {ch}: {hex(this_intensity)}')
        chargestamp_multiple(parser,path,ch,doAnalysis=True,fillzero=True,hvset=hvv,nevents=nevents,led_intensity=this_intensity,debug=options.debug,fillnan=True,analysis_startv=options.startv,prefat=True)

    end_time = time.time()
    print(f'Duration: {end_time - start_time:.1f} sec')
    with open(f'{path}/log.txt','a') as f:
        f.write(f'\nDuration: {end_time - start_time:.1f} sec')

def led_scan(parser,path,channel,led_setting,debug=False, basehv=None):
    this_path = f'{path}/led_scan'
    os.makedirs(this_path,exist_ok=True)
    qmean = chargestamp_led(parser,this_path,channel=channel,fillzero=True,nevents=1000,led_intensities=led_setting,debug=debug, basehv=basehv)
    return qmean

def chargestamp_led(parser, path, channel=None, doAnalysis=False, fillzero=False, nevents=None,debug=False,led_intensities=None,basehv=None):
    (options, args) = parser.parse_args()

    os.makedirs(f'{path}/raw',exist_ok=True)
    
    if channel is None:
        channel = int(options.channel)

    session = startIcebootSession(parser,host='localhost',port=5002)
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

    if not session.readLIDInterlock():
        os.system('python3 ../fh_icm_api/lid_enable.py')
    session.setDEggConstReadout(channel, 1, 256)
    session.setDEggExtTrigSourceICM()
    if options.hbuf:
        session.startDEggExternalHBufTrigStream(channel)
    else:
        session.startDEggExternalTrigStream(channel)
    session.disableDEggTriggers(1-channel)

    time.sleep(1)
    session.enableHV(channel)

    pdf = PdfPages(f'{path}/charge_histograms_ch{channel}.pdf')

    i = 0
    prev_setv = 0
    if basehv is not None:
        setv = int(basehv)
    else:
        setv = 1500

    session.setDEggHV(channel,int(setv))
    for j in (pbar := tqdm(range(int(abs(setv-prev_setv)/50+1)*2),leave=False)):
        pbar.set_description(f"Waiting for setv {setv} V")
        time.sleep(0.5)
    obs_qmean = []
    for i in tqdm(range(len(led_intensities)),desc='LED scan'):
        time.sleep(2)
        led_intensity = led_intensities[i]
        hdfout = f'{path}/raw/data_ch{channel}_{led_intensity}.hdf'
        led_off(session, True)
        time.sleep(1)
        #print(f'Set voltage: {setv} V')
        led_on(session, options.freq, led_intensity, setLEDon(1,False), True)
        time.sleep(1)
        try:
            datadic = charge_readout(session, options, channel, int(setv), hdfout, fillzero=fillzero, nevents=nevents, debug=debug, fillnan=True, prefat=True)
        except:
            traceback.print_exc()
            session.close()
            time.sleep(1)
            session = startIcebootSession(parser,host='localhost',port=5002)
            time.sleep(1)
            session.enableHV(channel)
            continue
        simple_plot_qhist(pdf, datadic, title=f'LED: {hex(led_intensity)}, SetV: {setv} V')
        qs = np.array(datadic['charge'])
        this_qmean = np.mean(qs[qs>-10])
        obs_qmean.append(this_qmean)
        prev_setv = setv
        if this_qmean > 16:
            print('exceeds 10 p.e. (assumed 1e7 gain) no need to take data above')
            break

    led_off(session, True)
    session.endStream()
    session.disableHV(channel)
    session.close()
    pdf.close()

    if doAnalysis:
        from analysis.qstamp_analyze import plot_scaled_charge_histogram_wrapper
        ana = plot_scaled_charge_histogram_wrapper(filepath=path,thzero=0.32,startv=1300,steps=250,channel=channel,do_fit_gain=options.gainfit)

    return obs_qmean

def LED_scaning(session, options, setv, led_intensities, channel, hvskip=False):
    if not hvskip:
        session.setDEggHV(channel,int(setv))
        for j in (pbar := tqdm(range(int(abs(setv-prev_setv)/50+1)*2),leave=False)):
            pbar.set_description(f"Waiting for setv {setv} V")
            time.sleep(0.5)
    obs_qmean = []
    for i in tqdm(range(len(led_intensities)),desc='LED scan'):
        time.sleep(2)
        led_intensity = led_intensities[i]
        hdfout = f'{path}/raw/data_ch{channel}_{led_intensity}.hdf'
        led_off(session, True)
        #print(f'Set voltage: {setv} V')
        led_on(session, options.freq, led_intensity, setLEDon(1,False), True)
        try:
            datadic = charge_readout(session, options, channel, int(setv), hdfout, fillzero=fillzero, nevents=nevents, debug=debug, fillnan=True, prefat=True)
        except:
            traceback.print_exc()
            session.close()
            time.sleep(1)
            session = startIcebootSession(parser)
            time.sleep(1)
            session.enableHV(channel)
            continue
        simple_plot_qhist(pdf, datadic, title=f'LED: {hex(led_intensity)}, SetV: {setv} V')
        qs = np.array(datadic['charge'])
        this_qmean = np.mean(qs[qs>-10])
        obs_qmean.append(this_qmean)
        prev_setv = setv
        if this_qmean > 10:
            print('exceeds 10 p.e. no need to take data above')
            break
    return obs_qmean

if __name__ == '__main__':
    main()
