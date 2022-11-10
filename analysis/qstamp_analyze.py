import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import tables
import click
import os,sys
from scipy.signal import argrelmax
from matplotlib.backends.backend_pdf import PdfPages
from tqdm import tqdm 
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

def gaus(x,a,mu,sigma):
    return a*np.exp(-(x-mu)**2/(2*sigma**2))

@click.group()
def cli():
    pass

@cli.command()
@click.option('--filepath',type=str,required=True)
def plot_charge_histogram(filepath):
    with tables.open_file(f'{filepath}/data.hdf') as f:
        data = f.get_node('/data')
        charges = data.col('charge')
        setvs = data.col('setv')

    with PdfPages(f'{filepath}/charge_histogram_offline.pdf') as pdf:
        for charge, setv in zip(charges, setvs):
            plt.hist(charge,bins=500,range=(-2,8),histtype='step')
            plt.xlabel('Charge [pC]')
            plt.ylabel('Entry')
            plt.yscale('log')
            plt.title(f'Set Voltage: {setv} V')
            pdf.savefig()
            plt.clf()

@cli.command()
@click.option('--filepath',type=str,required=True)
def plot_scaled_charge_histogram(filepath):
    with tables.open_file(f'{filepath}/data.hdf') as f:
        data = f.get_node('/data')
        charges = data.col('charge')
        setvs = data.col('setv')

    popts = []
    with PdfPages(f'{filepath}/charge_histogram_fit.pdf') as pdf:
        for charge, setv in zip(charges, setvs):
            threshold = 0.3+((setv-1200)/500)
            (hist_, bins_, _) = plt.hist(charge, bins=500, range=(-2,8), histtype='step')
            bin_center_ = np.array([(bins_[i]+bins_[i+1])/2 for i in range(len(bins_)-1)])
            popt, pcov = curve_fit(gaus, bin_center_[bin_center_>threshold], hist_[bin_center_>threshold])
            plt.plot(bin_center_, gaus(bin_center_,*popt),
                     label=f'SPE fit: $\mu=${popt[1]:.4f}, $\sigma=${abs(popt[2]):.4f}',color='tab:orange')
            plt.xlabel('Charge [pC]')
            plt.ylabel('Entry')
            plt.yscale('log')
            plt.ylim(0.5,np.exp(np.log(np.max(hist_))*1.2))
            plt.legend()
            plt.title(f'Set Voltage: {setv} V')
            pdf.savefig()
            plt.clf()
            popts.append(popt)

    with PdfPages(f'{filepath}/charge_histogram_scaled.pdf') as pdf:
        for charge, setv, popt in zip(charges, setvs, popts):
            (hist_,bins_,_) = plt.hist(charge/popt[1], bins=600, range=(-2,4), histtype='step')
            bin_center_ = np.array([(bins_[i]+bins_[i+1])/2 for i in range(len(bins_)-1)])
            threshold = (0.3+((setv-1200)/500))/popt[1]
            def fixed_gaus(x,a):
                return gaus(x,a,1,popt[2]/popt[1])
            popt2, _ = curve_fit(fixed_gaus, bin_center_[bin_center_>threshold], hist_[bin_center_>threshold])
            plt.plot(bin_center_, fixed_gaus(bin_center_,*popt2),
                     label=f'SPE fit:',color='tab:orange')
            plt.xlabel('# Photo-electrons')
            plt.ylabel('Entry')
            plt.yscale('log')
            plt.ylim(0.5,np.exp(np.log(np.max(hist_))*1.2))
            plt.title(f'Set Voltage: {setv} V')
            pdf.savefig()
            plt.clf()

    print(popts)
    plt.plot(setvs,[abs(popt[2]/popt[1]) for popt in popts],marker='o')
    plt.xlabel('Set Voltage [V]')
    plt.ylabel('Charge Resolution [p.e.]')
    plt.ylim(0,1.6)
    plt.savefig(f'{filepath}/charge_resolution.pdf')
    plt.clf()

if __name__ == '__main__':
    cli()
