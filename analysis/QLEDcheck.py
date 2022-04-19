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
def main(filepath, freq):
    fig = plt.figure()
    for i in range(12):
        filename = f'{filepath}/Run{i+1}/raw/test.hdf5'
        f = tables.open_file(filename)
        data = f.get_node('/data')
        charges = data.col('chargestamp')
        timestamps = data.col('timestamp')
        hv = data.col('hv')
        channel = data.col('channel')
        f.close()
        plt.hist(charges[0], bins=600, range=(-1,11), histtype='step',label=f'LED{i+1}',color=cm.brg(i/12))
        
    plt.xlabel('Charge [pC]')
    plt.ylabel('Entries')
    plt.yscale('log')
    plt.legend()
    plt.title(f'Charge Histogram ch#{channel[0]}, HV = {hv[0]} V')
    plt.tight_layout()
    plt.savefig(f'{filepath}/chargehist.pdf')
    plt.show()

if __name__=='__main__':
    main()
