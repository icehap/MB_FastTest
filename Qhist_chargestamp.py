#!/usr/bin/env python3

from iceboot.iceboot_session import getParser, startIcebootSession 
from addparser_iceboot import AddParser
import scope
import matplotlib.pyplot as plt
import matplotlib
import os, sys, time
import datetime
from pulserCalib import getThreshold
from mkplot import plotSetting
import tables
from tqdm import tqdm
from ROOT import TFile, TH1D, gROOT, gDirectory, TGraphErrors, TCanvas


def main(): 
    plotSetting(plt)
    matplotlib.rcParams['axes.xmargin'] = 0
    plt.rcParams['figure.figsize'] = [6.0,4.5]
    plt.rcParams['figure.subplot.right'] = 0.9
    
    parser = getParser()
    scope.AddParser(parser)
    
    (options, args) = parser.parse_args()
    
    nevents = int(options.nevents)
    snum = options.mbsnum 
    if len(snum.split('/')) > 1: 
        print('Do not use "/" in the MB serial number. Exit.')
        sys.exit(0)
    
    date = datetime.date.today()
    index = 1 
    prepath = f'results/QHist/{snum}/{date}/Run'
    path = prepath + str(index)
    
    while os.path.isdir(path):
        index = index + 1 
        path = prepath + str(index)
    
    
    print(f'=== File path is: {path}. ===')
    os.system(f'mkdir -p {path}')
    
    baseline = [0,0] 
    
    if options.filename is None: 
        print('Requires option: --filename.')
        print('Quit.')
        sys.exit(0)
    
    datapath = f'{path}/raw'
    os.system(f'mkdir -p {datapath}')
    
    hdfout_pre = f'{datapath}/{options.filename}'
    hdfout = f'{hdfout_pre}.hdf5'
    
    baselineset = 30450
    baseline = [8176, 8185]
    if options.measure_baselines: 
        baseline[0] = getThreshold(parser, 0, baselineset, 0, path)
        baseline[1] = getThreshold(parser, 1, baselineset, 0, path)

    if options.preset_baseline0 is not None: 
        baseline[0] = options.preset_baseline0
    if options.preset_baseline1 is not None:
        baseline[1] = options.preset_baseline1
    
    print(f'Measured baseline: {int(baseline[0])}, {int(baseline[1])}')
    
    # constants
    threshold_above_baseline = [9, 9] #72.59/10 # 0.1 p.e.
    hv = [1650,1750]
    if options.hv0 is not None: 
        hv[0] = options.hv0
    if options.hv1 is not None:
        hv[1] = options.hv1
    
    # ROOT 
    ofile = TFile(f'{hdfout_pre}.root',"RECREATE")
    h = [ROOTHistInit(0), ROOTHistInit(1)]

    for channel in range(2): 
        session = startIcebootSession(parser)
        session.flashConfigureFPGA("degg_fw_v0x10e.rbf.gz")
        session.enableHV(channel)
        session.setDEggHV(channel, hv[channel])
        time.sleep(2)
        HVobs = [session.readSloADC_HVS_Voltage(0), session.readSloADC_HVS_Voltage(1)]
        print(f'Observed HV Supply Voltages for channel {channel}: {HVobs[channel]} V.')
        
        session.setDAC('A',baselineset)
        time.sleep(1)
        session.setDAC('B',baselineset)
        time.sleep(1)
        session.setDEggConstReadout(0,1,128)
        session.setDEggConstReadout(1,1,128)
        #session.startDEggDualChannelTrigStream(
        #        baseline[0]+threshold_above_baseline,
        #        baseline[1]+threshold_above_baseline)
        starttime = time.time()
        session.startDEggThreshTrigStream(channel, baseline[channel]+threshold_above_baseline[channel])
        block = session.DEggReadChargeBlock(10,15,14*nevents,timeout=300)
        difftime = time.time() - starttime
        
        session.disableHV(channel)
        session.close()
        
        index = 0
        divpar = 100000
        charges = []
        #charges = [(rec.charge *1e12) for rec in block[channel] if not rec.flags]  
        for rec in tqdm(block[channel]):
            if rec.flags: 
                continue
            if index % divpar == 0: 
                hdfout = f'{hdfout_pre}_{int(index/divpar)}.hdf5'
            with tables.open_file(hdfout, 'a') as open_file: 
                try: 
                    table = open_file.get_node('/data')
                except: 
                    class Qdata(tables.IsDescription): 
                        event_id = tables.Int32Col()
                        timestamp = tables.Int64Col()
                        chargestamp = tables.Int64Col()
                        channel = tables.Int32Col()
                        hv = tables.Int32Col()
                        threshold = tables.Int32Col()
                    table = open_file.create_table('/', 'data', Qdata)
                    table = open_file.get_node('/data') 
    
                event = table.row
                event['event_id'] = index 
                event['timestamp'] = rec.timeStamp
                event['chargestamp'] = rec.charge*1e12
                event['hv'] = HVobs[channel]
                event['channel'] = channel
                event['threshold'] = baseline[channel] + threshold_above_baseline[channel]
    
            index += 1
            charges.append(rec.charge*1e12)
            h[channel].Fill(rec.charge*1e12)
    
    
        plt.figure().patch.set_facecolor('w')
        plt.hist(charges, bins=880, range=(-1,10), label=f'Channel {channel}', histtype="step", color="blue")
        plt.xlabel('Charge [pC]',ha='right',x=1.0)
        plt.ylabel('Entries',ha='right',y=1.0)
        plt.xlim(-1,5)
        plt.legend(title=f'HV: {HVobs[channel]:.2f} V \nThresh: {int(baseline[channel])}+{int(threshold_above_baseline[channel])} LSB \n#Events: {len(charges)} \nDuration: {difftime:.2f} sec')
        print(len(charges))
        
        plt.savefig(f'{path}/figure{channel}.pdf')
        h[channel].Write()
    
def ROOTHistInit(channel):
    hcharge = TH1D(f'qdist_{channel}',f'qdist_{channel};Charge [pC];Entry',1760,-1,10)
    return hcharge

if __name__ == '__main__':
    main()
