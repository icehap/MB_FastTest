#!/usr/bin/env python3

from iceboot.iceboot_session import getParser, startIcebootSession
import os, sys, time
import datetime

from measure_qstamp import chargestamp_multiple
import utils
import shared_options

def main():
    start_time = time.time()
    
    parser = getParser()
    shared_options.General(parser)
    shared_options.LED(parser)
    shared_options.Waveform(parser)
    parser.add_option('--deggnum',help='degg number',type=str,default='None')
    parser.add_option('--nevts',help='#wfs',default=None)
    (options, args) = parser.parse_args()
    path = utils.pathSetting(options, 'GainCheck', dedicated=f'{options.deggnum}')

    if options.hvv is None:
        hvv = '1200,1300,1400,1500,1600'
    else:
        hvv = options.hvv

    if options.nevts is not None:
        nevents = float(options.nevts)
    else:
        nevents = 50e3

    for ch in range(2):
        chargestamp_multiple(parser, path, ch, doAnalysis=True,fillzero=True,hvset=hvv,nevents=nevents)
    
    os.system(f'evince {path}/analysis_results_ch0.pdf &')
    os.system(f'evince {path}/analysis_results_ch1.pdf &')
    os.system(f'evince {path}/charge_histogram_fit_ch0.pdf &')
    os.system(f'evince {path}/charge_histogram_fit_ch1.pdf &')

    end_time = time.time()
    print(f'Duration: {end_time - start_time:.1f} sec')

if __name__ == '__main__':
    main()
