import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.ticker as ticker
import tables 
import click
import os, sys
from scipy.signal import argrelmax
from natsort import natsorted

lws = [1,2,1,1,2,1,1,2,1,1,2,1] # downward bold

@click.group()
def cli():
    pass

@cli.command()
@click.option('--filepath',type=str,required=True)
@click.option('--xmax',default=None)
@click.option('--rebin',type=int,default=1)
@click.option('--log/--no-log',default=True)
@click.option('--gain',default=None)
def main(filepath, xmax, rebin, log, gain):
    fig = plt.figure(figsize=(8,4.8))
    filename = f'{filepath}/raw/test.hdf5'
    f = tables.open_file(filename)
    data = f.get_node('/data')
    charges = data.col('chargestamp')
    timestamps = data.col('timestamp')
    hv = data.col('hv')
    channels = data.col('channel')
    ledbiass = data.col('ledbias')
    ledmasks = data.col('ledmask')
    ledperiods = data.col('ledperiod')
    f.close()

    if gain is not None:
        factor = 1.6 * float(gain)
        xlabel = 'Charge [PE]'
    else:
        factor = 1
        xlabel = 'Charge [pC]'
    
    binwidth = 0.1 * rebin
    maxcharge = int(np.max(charges)/factor/binwidth+1)*binwidth
    mincharge = int(np.min(charges)/factor/binwidth-1)*binwidth
    for i in range(12):
        plt.hist(charges[i]/factor, bins=int(maxcharge/binwidth-mincharge/binwidth+1), range=(mincharge,maxcharge), histtype='step',label=f'LED{i+1}',color=cm.brg(i/12), lw=lws[i])
        
    plt.xlabel(xlabel)
    plt.ylabel('Entries')
    if log:
        plt.yscale('log')
    plt.legend(bbox_to_anchor=(1,1), loc='upper left')
    plt.title(f'Charge Histogram ch#{channels[0]}, HV = {hv[0]} V, LED bias: {hex(ledbiass[0])}')
    if xmax is not None:
        plt.xlim(mincharge,float(xmax))
    plt.tight_layout()
    plt.savefig(f'{filepath}/chargehist.pdf')
    plt.show()

@cli.command()
@click.option('--filepath',type=str,required=True)
def vscan(filepath):
    fig = plt.figure(figsize=(8,4.8))
    filename = f'{filepath}/raw/test.hdf5'
    f = tables.open_file(filename)
    data = f.get_node('/data')
    channel = data.col('channel')
    hv = data.col('hv')
    charges = data.col('chargestamp')
    ledbias = data.col('ledbias')
    ledmask = data.col('ledmask')
    meancharge = np.mean(charges,axis=1)
    f.close()
    for i in range(12):
        if len(ledbias[np.log2(ledmask)==i]) > 0:
            plt.plot(ledbias[np.log2(ledmask)==i],meancharge[np.log2(ledmask)==i],lw=lws[i],label=f'LED{i+1}',color=cm.brg(i/12),ls='--')

    plt.title(f'Ch{channel[0]}, HV {np.mean(hv):.1f} V')
    plt.xlabel('Intensity Setting (hex)')
    plt.ylabel('Observed Mean Charge [pC]')
    plt.legend(bbox_to_anchor=(1,1), loc='upper left')
    
    axes = plt.gca()
    axes.get_xaxis().set_major_locator(ticker.MultipleLocator(2*16**2))
    axes.get_xaxis().set_major_formatter(ticker.FuncFormatter(lambda x, pos: '%x' % int(x)))
    
    plt.tight_layout()
    plt.savefig(f'{filepath}/LEDlumi.pdf')
    plt.yscale('log')
    plt.savefig(f'{filepath}/LEDlumi_log.pdf')
    plt.show()

@cli.command()
@click.option('--filepath',type=str,required=True)
def vscan_old(filepath):
    fig = plt.figure(figsize=(8,4.8))
    flist = natsorted(os.listdir(filepath))
    vflist = [f for f in flist if os.path.isdir(os.path.join(filepath, f))]
    qmeans = np.zeros((12,len(vflist)))
    masks = np.zeros(12)
    bias  = np.zeros((12,len(vflist)))
    for i, fname in enumerate(vflist):
        filename = f'{filepath}/{fname}/raw/test.hdf5'
        f = tables.open_file(filename)
        data = f.get_node('/data')
        charges = data.col('chargestamp')
        meancharges = np.mean(charges,axis=1)
        ledbiass = data.col('ledbias')
        ledmasks = data.col('ledmask')
        ledperiods = data.col('ledperiod')
        f.close()
        for j in range(12):
            qmeans[j][i] = np.mean(charges[j])
            masks[j] = ledmasks[j]
            bias[j][i] = ledbiass[j]

    for i in range(12):
        plt.plot(bias[i],qmeans[i],marker='o',lw=lws[i],label=f'LED{i+1}',color=cm.brg(i/12),ls='--')

    plt.xlabel('Intensity Setting (hex)')
    plt.ylabel('Observed Mean Charge [pC]')
    plt.legend(bbox_to_anchor=(1,1), loc='upper left')
    
    #def to_hex(x, pos):
    #    return '%x' % int(x)

    fmt = ticker.FuncFormatter(lambda x: '%x' % int(x))
    
    axes = plt.gca()
    axes.get_xaxis().set_major_locator(ticker.MultipleLocator(2*16**2))
    axes.get_xaxis().set_major_formatter(fmt)
    
    plt.tight_layout()
    plt.savefig(f'{filepath}/LEDlumi.pdf')
    plt.yscale('log')
    plt.savefig(f'{filepath}/LEDlumi_log.pdf')
    plt.show()

if __name__=='__main__':
    cli()
