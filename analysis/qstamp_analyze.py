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
from scipy import integrate

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
@click.option('--thzero',type=float,default=0.32)
@click.option('--startv',type=int,default=1300)
@click.option('--steps',type=int,default=250)
def plot_scaled_charge_histogram(filepath,thzero,startv,steps):
    with open(f'{filepath}/fit_config.txt','w') as f:
        f.write(f'th0: {thzero} \nstartv: {startv} \nsteps: {steps}')

    with tables.open_file(f'{filepath}/data.hdf') as f:
        data = f.get_node('/data')
        charges = data.col('charge')
        setvs = data.col('setv')
        hvvs = data.col('hvv')
        hvis = data.col('hvi')

    popts = []
    popts0 = []
    th0 = thzero
    pois_mean = []
    pois_err = []
    pedmin = -0.35
    pedth = 0.1
    with PdfPages(f'{filepath}/charge_histogram_fit.pdf') as pdf:
        for charge, setv in zip(charges, setvs):
            threshold = th0+((setv-startv)/steps)**2 if setv > startv else th0
            (hist_, bins_, _) = plt.hist(charge, bins=500, range=(-2,8), histtype='step')
            bin_center_ = np.array([(bins_[i]+bins_[i+1])/2 for i in range(len(bins_)-1)])
            
            # ped fitting
            popt0, pcov0 = curve_fit(gaus, bin_center_[(bin_center_<pedth) * (bin_center_>pedmin)], hist_[(bin_center_<pedth) * (bin_center_>pedmin)])
            n_ped_hist = gaus(bin_center_, *popt0)
            plt.plot(bin_center_, n_ped_hist, color='gray',ls='--',lw=1)
            plt.axvline(pedmin, ls=':', lw=0.5, color='gray', alpha=.5)
            plt.axvline(pedth,  ls=':', lw=0.5, color='gray', alpha=.5)

            pois_mean.append(-np.log(np.sum(n_ped_hist)/len(charge)))
            pois_err.append(1/np.sqrt(np.sum(n_ped_hist)))
            print(np.sum(n_ped_hist), len(charge))
            
            # spe fitting
            popt, pcov = curve_fit(gaus, bin_center_[bin_center_>threshold], hist_[bin_center_>threshold])
            plt.plot(bin_center_, gaus(bin_center_,*popt),
                     label=f'SPE fit: $\mu=${popt[1]:.4f}, $\sigma=${abs(popt[2]):.4f}',color='tab:orange')
            plt.axvline(threshold,linestyle=':',linewidth=1,color='magenta')
            plt.xlabel('Charge [pC]')
            plt.ylabel('Entry')
            plt.yscale('log')
            plt.ylim(0.5,np.exp(np.log(np.max(hist_))*1.2))
            plt.legend()
            plt.title(f'Set Voltage: {setv} V')
            pdf.savefig()
            plt.clf()
            popts.append(popt)
            popts0.append(popt0)

    with PdfPages(f'{filepath}/charge_histogram_scaled.pdf') as pdf:
        for charge, setv, popt in zip(charges, setvs, popts):
            (hist_,bins_,_) = plt.hist(charge/popt[1], bins=600, range=(-2,4), histtype='step')
            bin_center_ = np.array([(bins_[i]+bins_[i+1])/2 for i in range(len(bins_)-1)])
            threshold = (th0+((setv-startv)/steps)**2)/abs(popt[1]) if setv > startv else th0/abs(popt[1])
            
            if threshold > 4:
                threshold = 3
            def fixed_gaus(x,a):
                return gaus(x,a,1,popt[2]/popt[1])
            #print(setv, threshold, bin_center_[bin_center_>threshold], hist_[bin_center_>threshold])
            popt2, _ = curve_fit(fixed_gaus, bin_center_[bin_center_>threshold], hist_[bin_center_>threshold])
            def fixed_ped_gaus(x,a):
                return gaus(x,a,popt0[1]/popt[1],popt0[2]/popt[1])
            popt02, _ = curve_fit(fixed_ped_gaus, bin_center_[bin_center_<th0/popt[1]], hist_[bin_center_<th0/popt[1]])
            plt.plot(bin_center_, fixed_gaus(bin_center_,*popt2),
                     label=f'SPE fit:',color='tab:orange')
            #plt.plot(bin_center_, gaus(bin_center_,popt2[0],1,np.sqrt((popt[2]/popt[1])**2-(popt0[2]/popt[1])**2)))
            plt.axvline(threshold,linestyle=':',linewidth=1,color='magenta')
            plt.plot(bin_center_, fixed_ped_gaus(bin_center_,*popt02),color='gray',ls='--',lw=1)
            plt.xlabel('# Photo-electrons')
            plt.ylabel('Entry')
            plt.yscale('log')
            plt.ylim(0.5,np.exp(np.log(np.max(hist_))*1.2))
            plt.title(f'Set Voltage: {setv} V')
            pdf.savefig()
            plt.clf()

    print(popts)
    plt.plot(setvs,[np.sqrt((popt[2]/popt[1])**2-(popt0[2]/popt[1])**2) for popt,popt0 in zip(popts,popts0)],marker='o')
    plt.xlabel('Set Voltage [V]')
    plt.ylabel('Charge Resolution [p.e.]')
    plt.ylim(0,1.6)
    plt.grid(color='gray',linestyle=':',linewidth=1)
    plt.savefig(f'{filepath}/charge_resolution.pdf')
    plt.clf()

    plt.plot(setvs,[abs(popt0[2]) for popt0 in popts0],marker='o')
    plt.xlabel('Set Voltage [V]')
    plt.ylabel('Equivalent Noise Charge [pC]')
    plt.ylim(0,0.2)
    plt.savefig(f'{filepath}/noise.pdf')
    plt.clf()

    with PdfPages(f'{filepath}/poisson.pdf') as pdf:
        plt.errorbar(setvs, pois_mean, yerr=pois_err, marker='o', linestyle='')
        plt.xlabel('Set Voltage [V]')
        plt.ylabel('Poisson Mean [p.e.]')
        plt.grid(color='gray',linestyle=':',linewidth=1)
        plt.ylim(0,0.2)
        pdf.savefig()
        plt.clf()
        
        plt.hist(pois_mean, bins=100, range=(0,.2), histtype='step')
        plt.xlabel('Poisson Mean [p.e.]')
        plt.ylabel('Entry')
        pdf.savefig()
        plt.clf()

    epC = 1.60217663e-7
    gains = [(popt[1]-popt0[1])/epC for popt,popt0 in zip(popts,popts0)]
    plt.plot(setvs,gains,label='Set voltage',marker='o')
    plt.plot([np.mean(hvv) for hvv in hvvs],gains,label='Obs voltage',marker='o')
    plt.xlim(1000,2000)
    plt.xlabel('Voltage [V]')
    plt.ylabel('Gain')
    plt.grid(color='gray',linestyle=':',linewidth=1)
    plt.yscale('log')
    plt.legend()
    plt.savefig(f'{filepath}/gain.pdf')
    plt.clf()
 
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()

    ax1.plot(setvs,setvs,color='gray',ls='--',linewidth=1)
    ax1.errorbar(setvs,[np.mean(hvv) for hvv in hvvs],yerr=[np.std(hvv) for hvv in hvvs],label='Voltage',color='tab:blue')
    ax2.errorbar(setvs,[np.mean(hvi) for hvi in hvis],yerr=[np.std(hvi) for hvi in hvis],label='Current',color='tab:orange')
    ax1.set_xlabel('Set Voltage [V]')
    ax1.set_ylabel('Obs Voltage [V]')
    ax2.set_ylabel('Obs Current [$\mu$A]')

    ax2.set_ylim(0,20)
    
    h1,l1 = ax1.get_legend_handles_labels()
    h2,l2 = ax2.get_legend_handles_labels()

    ax1.legend(h1+h2,l1+l2)
    plt.savefig(f'{filepath}/hv_mon.pdf')
    plt.clf()


if __name__ == '__main__':
    cli()
