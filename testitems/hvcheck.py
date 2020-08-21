#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession 
from addparser_iceboot import AddParser
import time
import numpy as np 
import matplotlib.pyplot as plt 
from mkplot import plotSetting

def main(parser,path='.'):
    (options, args) = parser.parse_args()

    session = startIcebootSession(parser)
    
    session.setDEggHV(0,0)
    session.setDEggHV(1,0)
    time.sleep(5)
    
    HVsettings = np.arange(0,750,50)

    datapath = f'{path}/raw'

    for channel in range(2):
        hvvobs0, hvcobs0, hvverr0, hvcerr0 = getLists(session,HVsettings,channel)

        plotSetting(plt)
        plt.rcParams['figure.subplot.right'] = 0.9

        fig, ax1 = plt.subplots()

        ax1.set_xlabel('Set Value [V]', ha='right', x=1.0)
        ax1.set_ylabel('Observed Value [V]', ha='right', y=1.0)
        ax1.errorbar(HVsettings,hvvobs0,hvverr0,fmt='o-',color='black',label=f'Ch{channel} voltage')
        ax1.set_ylim(0,1000)
    
        ax2 = ax1.twinx()
        ax2.set_ylabel('Observed Value [$\mu$A]', ha='right', y=1.0, color='red')
        ax2.errorbar(HVsettings,hvcobs0,hvcerr0,fmt='o-',color='red',label=f'Ch{channel} current')
        ax2.set_ylim(0,50)
        ax2.spines['right'].set_color('red')
        ax2.tick_params(which='both',axis='y', colors='red')

        handler1, label1 = ax1.get_legend_handles_labels()
        handler2, label2 = ax2.get_legend_handles_labels()

        ax1.legend(handler1 + handler2, label1 + label2)
    
        fig.canvas.draw()
        fig.canvas.flush_events()
        plt.savefig(f'{datapath}/hv_{channel}.pdf')

    return ['hv_0.pdf','Comparison between set and observed HV values for channel 0.', 
            'hv_1.pdf','Comparison between set and observed HV values for channel 1.']

def getLists(session, HVsettings, channel):
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
        for j in range(10):
            hvv = readSloAdcChannel(session,8+2*channel)
            time.sleep(0.5)
            hvc = readSloAdcChannel(session,9+2*channel)
            time.sleep(0.5)
            hvvols.append(hvv)
            hvcurs.append(hvc)

        hvvobs.append(np.mean(hvvols))
        hvcobs.append(np.mean(hvcurs))
        hvverr.append(np.std(hvvols))
        hvcerr.append(np.std(hvcurs))

        print(f'Setting: {HVsettings[i]} V,  Obs.: {np.mean(hvvols)} +/- {np.std(hvvols)} V, {np.mean(hvcurs)} +/- {np.std(hvcurs)} uA')
    
    return hvvobs, hvcobs, hvverr, hvcerr


def readSloAdcChannel(session, channel):
    out = session.cmd("%d sloAdcReadChannel" % (channel)) 
    outlist = out.split()

    return float(outlist[3])
    
if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser)
    
