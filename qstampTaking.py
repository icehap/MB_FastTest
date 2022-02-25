#!/usr/bin/env python3

from iceboot.iceboot_session import getParser, startIcebootSession 
from addparser_iceboot import AddParser
import os, sys, time
import datetime
import tables
from testLED import doLEDflashing, setLEDon, disableLEDflashing
import numpy as np

import matplotlib
if os.getenv('BG') != None:
    matplotlib.use('Agg')

import matplotlib.pyplot as plt

def main(parser): 
    (options, args) = parser.parse_args()
    
    path = pathSetting(options,"QstampLED")

    f = open(f'{path}/log.txt','a')
    f.write(f'Run date: {datetime.datetime.now()}\n')
    f.write(f'{options}\n')
    
    takeChargeStamp(parser, path)
    f.write(f'Run end: {datetime.datetime.now()}\n')
    f.close()

def pathSetting(options, measname): 
    snum = options.mbsnum 
    if len(snum.split('/')) > 1: 
        print('Do not use "/" in the MB serial number. Exit.')
        sys.exit(0)
    
    date = datetime.date.today()
    index = 1
    if options.specific is not None:
        prepath = f'results/{measname}/{snum}/{date}/{options.specific}/Run'
    else:
        prepath = f'results/{measname}/{snum}/{date}/Run'
    path = prepath + str(index)

    while os.path.isdir(path):
        index = index + 1
        path = prepath + str(index)
    
    print(f'=== File path is: {path} ===')
    os.system(f'mkdir -p {path}')

    return path


def takeChargeStamp(parser, path='.'):
    (options, args) = parser.parse_args()

    nevents = int(options.nevents)

    if options.filename is None: 
        print('Requires option: --filename.')
        print('Quit.')
        sys.exit(0)
    
    session = startIcebootSession(parser)

    baselineset = 30000
    if len(options.dacSettings)==2:
        print(options.dacSettings)
        dacSet = options.dacSettings[0]
        baselineset = int(dacSet[1])
        session.setDAC(dacSet[0],baselineset)
    
    channel = int(options.channel)

    nSamples = (int(options.samples) / 4) *4
    if (nSamples < 16):
        print("Number of samples must be at least 16")
        sys.exit(1)

    session.setDEggConstReadout(channel, 1, int(nSamples))

    if int(options.hvv) > 0:
        session.enableHV(channel)
        session.setDEggHV(channel, int(options.hvv))
        print('Ramping HV...')
        time.sleep(60)
        HVobs = session.readSloADC_HVS_Voltage(channel)
        print(f'Observed HV Supply Voltages for channel {channel}: {HVobs} V.')
    
    session.setDEggExtTrigSourceICM()
    session.startDEggExternalTrigStream(channel)
    
    if options.scan:
        flashermasks = [setLEDon(i+1) for i in range(12)]
    else:
        flashermasks = str(options.flashermask).split(',')

    if options.vscan is not None:
        if options.vscan == "DEFAULT":
            biases = [0x5700,0x5800,0x5900,0x5A00,0x5B00,0x5C00,0x5D00,0x5E00,0x5F00,0x6000,0x6100,0x6200,0x6300,0x6400]
        else:
            biases = [int(f'{i}',16) for i in str(options.vscan).split(',')]
    else:
        biases = [options.intensity]

    if options.fscan is not None:
        freqs = [(options.fscan).split(',')]
    else:
        freqs = [options.freq]

    index = 0
    for ii, i in enumerate(flashermasks):
        if options.lscan=='horizontal':
            if ii==1 or ii==4 or ii==7 or ii==10:
                continue
        elif options.lscan=='vertical':
            if ii!=1 and ii!=4 and ii!=7 and ii!=10:
                continue
        for j in biases:
            for k in freqs:
                if options.led:
                    doLEDflashing(session, freq=k, bias=j, flashermask=i)
                storeChargeStampData(session, channel, options.filename, path, i, j, k, nevents, index)
                index += 1
                time.sleep(2)

    session.disableHV(channel)
    session.close()

    print('DONE!')

def storeChargeStampData(session, channel, filename, path, flashermask, intensity, freq, nevents, index=0):
    datapath = f'{path}/raw'
    os.system(f'mkdir -p {datapath}')
    os.system(f'mkdir -p {path}/plots')
    
    hdfout_pre = f'{datapath}/{filename}'
    hdfout = f'{hdfout_pre}.hdf5'
    
    channel = int(channel)
    HVobs = session.readSloADC_HVS_Voltage(channel)
    starttime = time.time()
    
    while(True):
        try:
            print(f"Taking charge block with the setting -- mask: {hex(flashermask)}, bias: {hex(intensity)}...")
            block = session.DEggReadChargeBlockFixed(140,155,14*nevents,timeout=300)
        except IOError:
            print("Timeout! Ending the session and will restart.")
            session.endStream()
            session.setDEggExtTrigSourceICM()
            session.startDEggExternalTrigStream(channel)
            n_retry += 1
            if n_retry == MAXNTRIAL:
                print("Something wrong. Skip.")
                session.close()
                break
            continue
        break

    difftime = time.time() - starttime
    print(f'done. Duration: {difftime:.2f} sec')
    disableLEDflashing(session)
    
    times = np.array([(rec.timeStamp) for rec in block[channel] if not rec.flags])
    charges = np.array([(rec.charge *1e12) for rec in block[channel] if not rec.flags])
    
    print(charges)
    with tables.open_file(hdfout, 'a') as open_file: 
        try: 
            table = open_file.get_node('/data')
        except: 
            class Qdata(tables.IsDescription): 
                timestamp = tables.Int64Col(shape=np.asarray(times).shape)
                chargestamp = tables.Float32Col(shape=np.asarray(charges).shape)
                channel = tables.Int32Col()
                hv = tables.Int32Col()
                ledbias = tables.Int64Col()
                ledmask = tables.Int64Col()
                ledperiod = tables.Int64Col()
            table = open_file.create_table('/', 'data', Qdata)
            table = open_file.get_node('/data') 
    
        event = table.row
        event['timestamp'] = times
        event['chargestamp'] = charges
        event['hv'] = HVobs
        event['channel'] = channel
        event['ledbias'] = int(intensity)
        event['ledmask'] = int(flashermask)
        event['ledperiod'] = int(freq)
        event.append()
        table.flush()
    
    fig = plt.figure()
    plt.hist(charges, bins=1000, range=(-1,max(charges)), histtype='step')
    plt.xlabel('Charge [pC]')
    plt.ylabel('Entries')
    plt.legend(title=f'HV: {HVobs:.2f} V \n#Events: {len(charges)} \nLED mask: {hex(flashermask)}\nLED bias: {hex(int(intensity))}\nLED period: {freq}\nDuration: {difftime:.2f} sec')
    plt.tight_layout()
    plt.savefig(f'{path}/plots/charge{index}.pdf')
    plt.yscale('log')
    plt.tight_layout()
    plt.savefig(f'{path}/plots/charge{index}_log.pdf')
    
    plt.clf()
    plt.close()
    
    
if __name__ == '__main__':
    parser = getParser()
    AddParser(parser)
    main(parser)
