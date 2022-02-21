import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import tables 
import click
import os, sys
from scipy.signal import argrelmax

@click.command()
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

    lws = [1,2,1,1,2,1,1,2,1,1,2,1] # downward bold
    
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

if __name__=='__main__':
    main()
