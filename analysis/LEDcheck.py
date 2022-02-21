import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import tables 
import click
import os, sys
from scipy.signal import argrelmax

@click.command()
@click.option('--filepath',type=str,required=True)
@click.option('--freq',type=int, default=5000)
@click.option('--channel',type=int,default=0)
@click.option('--spe', type=float,default=1)
@click.option('--save/--no-save',default=True)
@click.option('--qlog',is_flag=True)
def main(filepath, freq, channel, spe, save, qlog):
    chargeArray = []
    dtArray = []
    peakArray = []
    fig = plt.figure(figsize=(8,4.8))
    for i in range(12):
        filename = f'{filepath}/Run{i+1}/raw/test.hdf5'
        f = tables.open_file(filename)
        data = f.get_node('/data')
        waveforms = data.col('waveform')
        timestamps = data.col('timestamp')
        f.close()
        red_wfs = np.array([waveforms[ii] - np.mean(waveforms[ii][0:50]) for ii in range(len(waveforms))])
        charges = np.array([sum(red_wfs[ii][140:155]) for ii in range(len(waveforms))])
        chargeArray.append(charges)
        dt = np.array([(timestamps[j+1]-timestamps[j])/240.e6 for j in range(len(timestamps)-1)])
        dtArray.append(dt)
        
        peaks = []
        for ii in range(len(waveforms)): 
            peak_can = argrelmax(red_wfs[ii], order=10)
            yvalue = 0
            peak_index = 0
            for j in peak_can[0]:
                yvalue_can = red_wfs[ii][j]
                if yvalue < yvalue_can:
                    yvalue = yvalue_can
                    peak_index = j
            peaks.append(peak_index)
        peakArray.append(np.array(peaks))

    nsamples = len(waveforms[0])
    itrdur = 17.0666667e-6 * freq

    lws = [1,2,1,1,2,1,1,2,1,1,2,1] # downward bold
    nbins = 101
    maxcharge = int(np.mean(np.array(chargeArray))/50)*100/spe
    mincharge = int(np.mean(np.array(chargeArray))/50)*(-5)/spe
    if maxcharge < int(np.max(np.array(chargeArray))/100)*100/spe: 
        maxcharge = int(np.max(np.array(chargeArray))/100)*100/spe
        mincharge = int(np.max(np.array(chargeArray))/100)*(-1)/spe
    for i in range(12):
        plt.hist(chargeArray[i]/spe, bins=nbins, range=(mincharge,maxcharge), histtype='step',label=f'LED{i+1}',color=cm.brg(i/12),lw=lws[i])
    if spe==1:
        plt.xlabel('Charge [ADC]')
    else: 
        plt.xlabel('Charge [PE]')
    plt.ylabel('Entries')
    if qlog: 
        plt.yscale('log')
    plt.legend(bbox_to_anchor=(1,1), loc='upper left')
    plt.title(f'Charge histogram: ch#{channel}')
    plt.tight_layout()
    if save: 
        plt.savefig(f'{filepath}/charge.pdf')
    plt.show()

    plt.axvline(itrdur*1e3,ls=':',color='magenta',lw=1)
    #plt.axvline(2*itrdur*1e3,ls=':',color='magenta',lw=0.5)
    #plt.axvline(3*itrdur*1e3,ls=':',color='magenta',lw=0.5)
    for i in range(12):
        plt.hist(dtArray[i]*1e3, bins=2400, range=(0,300), histtype='step',label=f'LED{i+1}',color=cm.brg(i/12))
    plt.xlabel('Time difference [ms]')
    plt.ylabel('Entries')
    plt.yscale('log')
    plt.legend(loc='upper left')
    plt.title(f'$\Delta t$: ch#{channel}')
    plt.tight_layout()
    plt.savefig(f'{filepath}/Dtimestamps.pdf')
    plt.xlim(250,260)
    if save:
        plt.savefig(f'{filepath}/Dtimestamps_expand.pdf')
    plt.show()

    plt.axvline(0,ls=':',color='black',lw=1)
    for i in range(12):
        reduced_dt = []
        for ii in dtArray[i]:
            reddt = ii - itrdur 
            while reddt > 0.5 * itrdur: 
                reddt -= itrdur
            reduced_dt.append(reddt)
        plt.hist(np.array(reduced_dt)*1e9, bins=1000, range=(-50,50), histtype='step',label=f'LED{i+1}',color=cm.brg(i/12))
    plt.xlabel('Time difference [ns]')
    plt.ylabel('Entries')
    plt.yscale('log')
    plt.legend(loc='upper left')
    plt.title(f'$\Delta t$ $-$ flashing period: ch#{channel}')
    plt.tight_layout()
    if save:
        plt.savefig(f'{filepath}/reduced_Dtime.pdf')
    plt.show()


    for i in range(12):
        plt.hist(peakArray[i], bins=nsamples, range=(0,nsamples), histtype='step',label=f'LED{i+1}',color=cm.brg(i/12))
    plt.xlabel('Sampling bins')
    plt.ylabel('Entries')
    plt.yscale('log')
    plt.legend()
    plt.title(f'Peak position in the window: ch#{channel}')
    plt.tight_layout()
    if save:
        plt.savefig(f'{filepath}/peakposition.pdf')
    plt.xlim(135,160)
    if save:
        plt.savefig(f'{filepath}/peakposition_expand.pdf')
    plt.show()

if __name__=='__main__':
    main()
