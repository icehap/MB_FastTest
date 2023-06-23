from iceboot.iceboot_session import getParser, startIcebootSession
from iceboot.test_waveform import parseTestWaveform, applyPatternSubtraction
import numpy as np
import tables
import matplotlib.pyplot as plt
import time, os, sys
import traceback
from sensorcheck import readSloAdcChannel
from tqdm import tqdm

def get_waveform(session, options, setv, filename,channel=None):
    if channel is None:
        channel = options.channel
    while session.fpgaVersion()==65535:
        firmware_name = 'degg_fw_v0x110.rbf.gz'
        session.flashConfigureCycloneFPGA(firmware_name)

    try:
        readout = parseTestWaveform(session.readWFMFromStream())
    except IOError:
        traceback.print_exc()
        time.sleep(1)
    
    if readout is None:
        raise Exception

    datadic = dict_init(options)
    datadic['waveform'] = np.asarray(readout['waveform'])
    datadic['timestamp'] = readout['timestamp']
    datadic['pc_time'] = time.time()
    datadic['temperature'] = session.readSloADCTemperature()
    datadic['channel'] = channel
    datadic['hvs'] = np.array([float(setv), 
                               float(session.readSloADC_HVS_Voltage(channel)), 
                               float(session.readSloADC_HVS_Current(channel))])
    datadic['mbvrail'] = np.array([readSloAdcChannel(session,12),
                                   readSloAdcChannel(session,13),
                                   readSloAdcChannel(session,5),
                                   readSloAdcChannel(session,14),
                                   readSloAdcChannel(session,15)])
    datadic['mbirail'] = np.array([readSloAdcChannel(session,0),
                                   readSloAdcChannel(session,1),
                                   readSloAdcChannel(session,2),
                                   readSloAdcChannel(session,3),
                                   readSloAdcChannel(session,4)])

    store_hdf(filename, datadic)

    return datadic

def dict_init(options):
    return {'waveform'   : np.zeros(options.samples),
            'timestamp'  : -1,
            'pc_time'    : -1,
            'temperature': -293,
            'hvs'        : np.array([-1,-1,-1]), #Vset, Vobs, Iobs 
            'channel'    : -1,
            'mbvrail'    : np.array([-1,-1,-1,-1,-1]),
            'mbirail'    : np.array([-1,-1,-1,-1,-1])
            }

def store_hdf(filename,datadic):
    with tables.open_file(filename,'a') as f:
        try:
            table = f.get_node('/data')
        except:
            class Event(tables.IsDescription):
                waveform = tables.Int32Col(shape=np.asarray(datadic['waveform']).shape)
                timestamp = tables.Int64Col()
                pc_time = tables.Float32Col()
                temperature = tables.Float32Col()
                hvs = tables.Float32Col(shape=np.asarray(datadic['hvs']).shape)
                channel = tables.Int32Col()
                mbvrail = tables.Float32Col(shape=np.asarray(datadic['mbvrail']).shape)
                mbirail = tables.Float32Col(shape=np.asarray(datadic['mbirail']).shape)
            table = f.create_table('/','data',Event)
            table = f.get_node('/data')
        event = table.row
        for key in datadic:
            event[key] = datadic[key]
        event.append()
        table.flush()

def start_single_waveform_stream(session, options):
    session.setDEggConstReadout(options.channel, 2, int(options.samples))
    if options.external: 
        print('External trigger mode')
        session.startDEggExternalTrigStream(options.channel)
    elif options.threshold is None:
        print(f'Software trigger mode with trig delay of {options.swTrigDelay}')
        session.startDEggSWTrigStream(options.channel, options.swTrigDelay)
    else:
        print(f'Threshold trigger mode with trig threshold of {options.threshold}')
        session.startDEggThreshTrigStream(options.channel, options.threshold)

def get_baseline(session, options, path, channel=None):
    os.makedirs(f'{path}/calib',exist_ok=True)
    if channel is None:
        channel = options.channel
        outfilename = f'{path}/calib/baseline.hdf5'
    else:
        outfilename = f'{path}/calib/baseline_ch{channel}.hdf5'
    session.startDEggSWTrigStream(channel, options.swTrigDelay)
    wf = []
    for i in tqdm(range(50),desc='[baseline]',leave=False):
        datadic = get_waveform(session, options, setv=0, filename=outfilename, channel=channel)
        wf.append(datadic['waveform'])
    session.endStream()
    baseline = np.mean(np.array(wf))
    return int(baseline)
