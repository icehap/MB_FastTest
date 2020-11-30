#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession 
from addparser_iceboot import AddParser
import time
import tables
import os
import numpy as np 
import matplotlib.pyplot as plt 
from mkplot import plotSetting
from matplotlib import gridspec
from loadFPGA import loadFPGA

def main(parser,path='.'):
    (options, args) = parser.parse_args()
    hvbnums = (options.hvbnums).split(',')

    session = startIcebootSession(parser)
    
    session.setDEggHV(0,0)
    session.setDEggHV(1,0)
    time.sleep(1)
    
    HVsettings = np.arange(0,1500,20)

    datapath = f'{path}/raw'


    for channel in range(2):
        hvvobs0, hvcobs0, hvverr0, hvcerr0 = getLists(session,HVsettings,channel,hvbnums,datapath)

        plotSetting(plt)
        plt.rcParams['figure.figsize'] = [8.0,7.0]
        plt.rcParams['figure.subplot.right'] = 0.9

        #fig, ax1 = plt.subplots()
        fig = plt.figure()
        spec = gridspec.GridSpec(ncols=1,nrows=2,height_ratios=[3,1],hspace=0.05)
        ax1 = fig.add_subplot(spec[0])
        axr = fig.add_subplot(spec[1])

        ## top plot 
        #ax1.set_xlabel('Set Value [V]', ha='right', x=1.0)
        ax1.set_ylabel('Observed Voltage $V_\mathrm{obs}$ [V]', ha='right', y=1.0)
        ax1.errorbar(HVsettings,hvvobs0,hvverr0,fmt='o-',color='black',label=f'Ch{channel} voltage')
        ax1.set_ylim(0,2000)
        ax1.tick_params(labelbottom=False)
    
        ax2 = ax1.twinx()
        ax2.set_ylabel('Observed Current $I_\mathrm{obs}$ [$\mu$A]', ha='right', y=1.0, color='red')
        ax2.errorbar(HVsettings,hvcobs0,hvcerr0,fmt='o-',color='red',label=f'Ch{channel} current')
        ax2.set_ylim(0,40)
        ax2.spines['right'].set_color('red')
        ax2.tick_params(which='both',axis='y', colors='red')

        handler1, label1 = ax1.get_legend_handles_labels()
        handler2, label2 = ax2.get_legend_handles_labels()

        ax1.legend(handler1 + handler2, label1 + label2)
    
        ## bottom plot
        axr.set_xlabel('Set Voltage $V_\mathrm{set}$ [V]', ha='right', x=1.0)
        axr.set_ylabel(r'$\dfrac{V_\mathrm{obs}-V_\mathrm{set}}{V_\mathrm{set}}$ [%]', ha='right', y=1.0)
        HVsettingNonZero = HVsettings
        HVsettingNonZero[0] = 1
        print(HVsettingNonZero)
        diffhv = (np.array(hvvobs0) - HVsettings)/HVsettingNonZero*100
        axr.errorbar(HVsettings,diffhv,hvverr0,fmt='o-',color='black')
        axr.set_ylim(-7,7)
        
        if options.b: 
            fig.canvas.draw()
            fig.canvas.flush_events()
        plt.savefig(f'{datapath}/hv{hvbnums[channel]}_{channel}.pdf')

    session.setDEggHV(0,0)
    session.setDEggHV(1,0)
    session.disableHV(0)
    session.disableHV(1)

    return [f'hv{hvbnums[0]}_0.pdf','Comparison between set and observed HV values for channel 0.', 
            f'hv{hvbnums[1]}_1.pdf','Comparison between set and observed HV values for channel 1.']

def getLists(session, HVsettings, channel, hvbnums, datapath='.'):
    hvvobs = []
    hvcobs = []
    hvverr = []
    hvcerr = []
    
    print(f'Scan for channel {channel}.')
    for i in range(len(HVsettings)):
        session.setDEggHV(channel, HVsettings[i])
        session.enableHV(channel)
        time.sleep(0.5)
        
        hvvols = []
        hvcurs = []
        for j in range(5):
            hvv = readSloAdcChannel(session,8+2*channel)
            time.sleep(0.01)
            hvc = readSloAdcChannel(session,9+2*channel)
            time.sleep(0.01)
            hvvols.append(hvv)
            hvcurs.append(hvc)

        hvvobs.append(np.mean(hvvols))
        hvcobs.append(np.mean(hvcurs))
        hvverr.append(np.std(hvvols))
        hvcerr.append(np.std(hvcurs))

        with tables.open_file(f'{datapath}/hv{hvbnums[0]}_{hvbnums[1]}.hdf5','a') as open_file: 
            try: 
                table = open_file.get_node('/hvmon')
            except: 
                class HVmon(tables.IsDescription):
                    channel = tables.Int32Col()
                    HVVset = tables.Int32Col()
                    HVVobs = tables.Float32Col()
                    HVVerr = tables.Float32Col()
                    HVCobs = tables.Float32Col()
                    HVCerr = tables.Float32Col()
                table = open_file.create_table('/','hvmon',HVmon)
                table = open_file.get_node('/hvmon')

            hvmon = table.row
            hvmon['channel'] = channel
            hvmon['HVVset'] = HVsettings[i]
            hvmon['HVVobs'] = np.mean(hvvols)
            hvmon['HVVerr'] = np.std(hvvols)
            hvmon['HVCobs'] = np.mean(hvcurs)
            hvmon['HVCerr'] = np.std(hvcurs)
            hvmon.append()
            table.flush()

        print(f'Setting: {HVsettings[i]} V,  Obs.: {np.mean(hvvols):.03f} +/- {np.std(hvvols):.03f} V, {np.mean(hvcurs):.03f} +/- {np.std(hvcurs):.03f} uA')
    
    return hvvobs, hvcobs, hvverr, hvcerr


def readSloAdcChannel(session, channel):
    out = session.cmd("%d sloAdcReadChannel" % (channel)) 
    outlist = out.split()

    return float(outlist[3])
    
if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    (options, args) = parser.parse_args()
    hvbnums = (options.hvbnums).split(',')
    if len(hvbnums)!=2: 
        print("Please set --hvbnums like '100,101'... Quit.")
        exit(1)

    loadFPGA(parser)
    path = os.getenv('FTHOME') + f'/results/HVCheck/{options.mbsnum}'
    os.system(f'mkdir -p {path}/raw')
    main(parser,path)
    
