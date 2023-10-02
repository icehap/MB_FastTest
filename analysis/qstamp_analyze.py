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
import datetime

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
            plt.hist(charge,bins=700,range=(-2,10),histtype='step')
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
@click.option('--gainfit',is_flag=True,default=False)
@click.option('--channel',type=int,default=None)
@click.option('--qmax',default=None)
@click.option('--bestscale',is_flag=True,default=False)
@click.option('--linear',is_flag=True,default=False)
def plot_scaled_charge_histogram(filepath,thzero,startv,steps,gainfit,qmax,channel,bestscale,linear):
    plot_scaled_charge_histogram_wrapper(filepath,thzero,startv,steps,channel=channel,qmax=qmax,do_gain_fit=gainfit,offline=True,bestScale=bestscale,lingood=linear)

def plot_scaled_charge_histogram_wrapper(filepath,thzero,startv,steps,channel=None,qmax=None,do_gain_fit=False,offline=False,bestScale=False,lingood=False):
    with open(f'{filepath}/fit_config.txt','a') as f:
        f.write(f'channel: {channel}\n')
        f.write(f'th0: {thzero}\nstartv: {startv}\nsteps: {steps}\n')

    tablepath = f'{filepath}/raw/data.hdf'
    if channel is not None:
        tablepath = f'{filepath}/raw/data_ch{channel}.hdf'

    with tables.open_file(tablepath) as f:
        data = f.get_node('/data')
        charges = data.col('charge')
        setvs = data.col('setv')
        hvvs = data.col('hvv')
        hvis = data.col('hvi')

    charge_analyze(charges=charges,setvs=setvs,hvvs=hvvs,hvis=hvis,filepath=filepath,thzero=thzero,startv=startv,steps=steps,channel=channel,qmax=qmax,do_gain_fit=do_gain_fit,offline=offline,bestScale=bestScale,lingood=lingood)

def charge_analyze(charges,setvs,hvvs,hvis,filepath,thzero,startv,steps,channel=None,qmax=None,do_gain_fit=False,cr_xaxis=None,out=None,lingood=False,offline=False,bestScale=False,fixedfitrange=None):

    popts = []
    popts0 = []
    th0 = thzero
    pois_mean = []
    pois_err = []
    pedmin = -0.35
    pedth = 0.1
    
    suffix = '' if channel is None else f'_ch{channel}'
    if out is not None:
        suffix += f'_{out}'
    if offline:
        suffix += '_offline'
    pdf = PdfPages(f'{filepath}/charge_histogram_fit{suffix}.pdf')
    linearPdf = PdfPages(f'{filepath}/Linear_charge_histogram_fit{suffix}.pdf')
    if qmax is not None:
        binmax = float(qmax)
    else:
        binmax = 10

    if lingood:
        lingood_ymax_ = []
        for charge, setv in zip(charges, setvs):
            threshold = th0+((setv-startv)/steps)**2 if setv > startv else th0
            (hist_, bins_, _) = plt.hist(charge, bins=1600, range=(-2,30), histtype='step')
            bin_center_ = np.array([(bins_[i]+bins_[i+1])/2 for i in range(len(bins_)-1)])
            lingood_ymax_.append(np.max(hist_[bin_center_>threshold]))
            plt.clf()
        lingood_ymax = int(np.max(lingood_ymax_) * 1.2 / 10) * 10
        lingoodpdf = PdfPages(f'{filepath}/lin_charge_histogram_fit{suffix}.pdf') 


    for charge, setv in zip(charges, setvs):
        threshold = th0+((setv-startv)/steps)**2 if setv > startv else th0
        (hist_, bins_, _) = plt.hist(charge, bins=1600, range=(-2,30), histtype='step')
        bin_center_ = np.array([(bins_[i]+bins_[i+1])/2 for i in range(len(bins_)-1)])
        
        # ped fitting
        try:
            popt0, pcov0 = curve_fit(gaus, bin_center_[(bin_center_<pedth) * (bin_center_>pedmin)], hist_[(bin_center_<pedth) * (bin_center_>pedmin)])
        except:
            popt0 = [0,0,0]
        n_ped_hist = gaus(bin_center_, *popt0)
        plt.plot(bin_center_, n_ped_hist, color='gray',ls='--',lw=1)
        plt.axvline(pedmin, ls=':', lw=0.5, color='gray', alpha=.5)
        plt.axvline(pedth,  ls=':', lw=0.5, color='gray', alpha=.5)

        pois_mean.append(-np.log(np.sum(n_ped_hist)/len(charge)))
        pois_err.append(1/np.sqrt(np.sum(n_ped_hist)))
        #print(np.sum(n_ped_hist), len(charge))
        
        # spe fitting
        #try:
        #    popt, pcov = curve_fit(gaus, bin_center_[bin_center_>threshold], hist_[bin_center_>threshold])
        #except RuntimeError:
        #    subt_ped_ = hist_ - gaus(bin_center_,popt0[0],popt0[1],popt0[2]) 
        #    popt, pcov = curve_fit(gaus, bin_center_[bin_center_>threshold], subt_ped_[bin_center_>threshold])
        
        subt_ped_ = hist_ - gaus(bin_center_,*popt0) 
        #plt.axvline(threshold,linestyle=':',linewidth=1,color='green')
        if popt0[1]+4*popt0[2] > threshold:
            threshold = popt0[1] + 4*popt0[2]
        spe_fit_range = (bin_center_>threshold) 
        if cr_xaxis is not None:
            spe_fit_range *= (bin_center_<3)
        if fixedfitrange is not None:
            fix_x = str(fixedfitrange).split(',')
            if len(fix_x) == 2:
                try:
                    spe_fit_range = (bin_center_ > float(fix_x[0])) * (bin_center_ < float(fix_x[1]))
                except:
                    print(f'WARNING: Something wrong with the fixed fit range setting.')
                    pass
        try: 
            popt, pcov = curve_fit(gaus, bin_center_[spe_fit_range], subt_ped_[spe_fit_range])
        except: 
            try:
                popt, pcov = curve_fit(gaus, bin_center_, subt_ped_)
            except:
                popt = [0,0,0]

        #plt.plot(bin_center_, subt_ped_, ds='steps-mid', lw=1, ls=':', color='magenta')
        plt.plot(bin_center_, gaus(bin_center_,*popt),
                 label=f'SPE fit: $\mu=${popt[1]:.4f}, $\sigma=${abs(popt[2]):.4f}',color='tab:orange')
        plt.axvline(threshold,linestyle=':',linewidth=1,color='magenta')
        plt.xlabel('Charge [pC]')
        plt.ylabel('Entry')
        plt.legend()
        plt.title(f'Set Voltage: {setv} V')
        plt.xlim(-2,binmax)
        linearPdf.savefig()
        plt.ylim(0.5,np.exp(np.log(np.max(hist_))*1.2))
        plt.yscale('log')
        pdf.savefig()

        if lingood:
            plt.yscale('linear')
            plt.xlim(-2,6)
            plt.ylim(0,lingood_ymax)
            lingoodpdf.savefig()

        plt.clf()

        popts.append(popt)
        popts0.append(popt0)

    pdf.close()
    linearPdf.close()
    if lingood:
        lingoodpdf.close()

    '''
    with PdfPages(f'{filepath}/charge_histogram_scaled{postfix}.pdf') as pdf:
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
            try:
                popt02, _ = curve_fit(fixed_ped_gaus, bin_center_[bin_center_<th0/popt[1]], hist_[bin_center_<th0/popt[1]])
            except:
                popt02, _ = curve_fit(fixed_ped_gaus, bin_center_ , hist_)
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
    '''

    xdata = setvs if cr_xaxis is None else cr_xaxis
    vol_label = 'Set Voltage [V]' if cr_xaxis is None else 'Fluctuation Half-Width [V]'
    with PdfPages(f'{filepath}/analysis_results{suffix}.pdf') as pdf:
        epC = 1.60217663e-7
        gains = [(popt[1]-popt0[1])/epC if popt[0] > 0 else np.nan for popt,popt0 in zip(popts,popts0)]
        if cr_xaxis is None:
            plt.plot(setvs,gains,label='Set voltage',marker='o')
            mean_hvs = [np.mean(hvv) for hvv in hvvs]
            plt.plot(mean_hvs,gains,label='Obs voltage',marker='o')
            if do_gain_fit:
                def gain_curve(x,a,b):
                    return a*x**b
                popts_gain, _ = curve_fit(gain_curve,setvs,gains)
                x_range = np.linspace(setvs[0],setvs[-1],1000)
                fit_gain = gain_curve(x_range,*popts_gain)
                plt.plot(x_range,fit_gain,color='blue')
                subt_fit_gain = fit_gain - 1e7
                hv_at_1e7 = (x_range[subt_fit_gain>0])[0]
                print(hv_at_1e7)
            if not bestScale:
                plt.xlim(1000,2000)
            plt.xlabel('Voltage [V]')
        else:
            plt.plot(xdata,gains,marker='o',markersize=1)
            plt.xlabel('Fluctuation Half-Width [V]')
        plt.ylabel('Gain')
        plt.grid(color='gray',linestyle=':',linewidth=1)
        plt.legend()
        plt.title('Gain Curve')
        pdf.savefig()
        plt.yscale('log')
        pdf.savefig()
        plt.clf()
 
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()

        if cr_xaxis is None:
            ax1.plot(setvs,setvs,color='gray',ls='--',linewidth=1)
            ax1.errorbar(xdata,[np.mean(hvv) for hvv in hvvs],yerr=[np.std(hvv) for hvv in hvvs],label='Voltage',color='tab:blue')
            ax2.errorbar(xdata,[np.mean(hvi) for hvi in hvis],yerr=[np.std(hvi) for hvi in hvis],label='Current',color='tab:orange')
        else:
            ax1.errorbar(xdata,[hvv[0] for hvv in hvvs],yerr=[np.sqrt(hvv[1]) for hvv in hvvs],label='Voltage',color='tab:blue')
            ax2.errorbar(xdata,[hvi[0] for hvi in hvis],yerr=[np.sqrt(hvi[1]) for hvi in hvis],label='Current',color='tab:orange')
        ax1.set_xlabel('Set Voltage [V]')
        ax1.set_ylabel('Obs Voltage [V]')
        ax2.set_ylabel('Obs Current [$\mu$A]')
        plt.title('HV mon')

        ax2.set_ylim(0,20)
        
        h1,l1 = ax1.get_legend_handles_labels()
        h2,l2 = ax2.get_legend_handles_labels()

        ax1.legend(h1+h2,l1+l2)
        pdf.savefig()
        plt.clf()

        try:
            plt.plot(xdata,[np.sqrt((popt[2]/popt[1])**2-(popt0[2]/popt[1])**2) if popt[0] > 0 else np.nan for popt,popt0 in zip(popts,popts0)],marker='o',markersize=1)
        except:
            pass
        plt.xlabel(vol_label)
        plt.ylabel('Charge Resolution [p.e.]')
        plt.ylim(0,1.6)
        plt.grid(color='gray',linestyle=':',linewidth=1)
        plt.title('Charge Resolution')
        pdf.savefig()
        plt.clf()

        plt.plot(xdata,[abs(popt0[2]) for popt0 in popts0],marker='o',markersize=1)
        plt.xlabel(vol_label)
        plt.ylabel('Equivalent Noise Charge [pC]')
        plt.ylim(0,0.2)
        plt.title('Noise')
        pdf.savefig()
        plt.clf()

        plt.errorbar(xdata, pois_mean, yerr=pois_err, marker='o', linestyle='',markersize=1)
        plt.xlabel(vol_label)
        plt.ylabel('Poisson Mean [p.e.]')
        plt.grid(color='gray',linestyle=':',linewidth=1)
        plt.ylim(0,0.2)
        plt.title('Poisson Mean')
        pdf.savefig()
        plt.clf()
        
        plt.hist(pois_mean, bins=100, range=(0,.2), histtype='step')
        plt.xlabel('Poisson Mean [p.e.]')
        plt.ylabel('Entry')
        plt.title('Poisson Mean')
        pdf.savefig()
        plt.clf()

@cli.command()
@click.option('--filepath',type=str,required=True)
@click.option('--thzero',type=float,default=0.32)
@click.option('--startv',type=int,default=1300)
@click.option('--steps',type=int,default=250)
@click.option('--channel',type=int,default=0)
def gainplot(filepath,thzero,startv,steps,channel):
    gain_estimate(filepath,thzero,startv,steps,channel)

def gain_estimate(filepath,thzero,startv,steps,channel=0,qmax=None):
    tablepath = f'{filepath}/raw/data_ch{channel}.hdf'

    with tables.open_file(tablepath) as f:
        data = f.get_node('/data')
        charges = data.col('charge')
        setvs = data.col('setv')
        hvvs = data.col('hvv')
        pctimes = data.col('pctime')

    popts = []
    popts0 = []
    th0 = thzero
    pedmin = -0.35
    pedth = 0.1

    for charge, setv in zip(charges, setvs):
        threshold = th0+((setv-startv)/steps)**2 if setv > startv else th0
        (hist_, bins_, _) = plt.hist(charge, bins=1600,range=(-2,30), histtype='step')
        bin_center_ = np.array([(bins_[i]+bins_[i+1])/2 for i in range(len(bins_)-1)])

        #ped fitting
        try:
            popt0, pcov0 = curve_fit(gaus, bin_center_[(bin_center_<pedth) * (bin_center_>pedmin)], hist_[(bin_center_<pedth)*(bin_center_>pedmin)])
        except:
            popt0 = [0,0,0]
        popts0.append(popt0)

        #spe fitting
        subt_ped_ = hist_ - gaus(bin_center_,*popt0)
        if popt0[1]+4*popt0[2] > threshold:
            threshold = popt0[1] + 4*popt0[2]
        try:
            popt, pcov = curve_fit(gaus, bin_center_[bin_center_>threshold], subt_ped_[bin_center_>threshold])
        except:
            try: 
                popt, pcov = curve_fit(gaus, bin_center_, subt_ped_)
            except:
                popt = [0,0,0]
        popts.append(popt)

    epC = 1.60217663e-7
    gains = [(popt[1]-popt0[1])/epC for popt,popt0 in zip(popts,popts0)]

    gain_dict = {}
    time_dict = {}
    obsv_dict = {}
    obsv_sigma_dict = {}
    for i, setv in enumerate(setvs):
        gain = gains[i]
        gain_dict.setdefault(str(setv),[])
        gain_dict[str(setv)].append(gain)

        time_dict.setdefault(str(setv),[])
        time_dict[str(setv)].append(datetime.datetime.fromtimestamp(int(pctimes[i])))

        obsv_dict.setdefault(str(setv),[])
        obsv_dict[str(setv)].append(np.mean(hvvs[i]))

        obsv_sigma_dict.setdefault(str(setv),[])
        obsv_sigma_dict[str(setv)].append(np.std(hvvs[i]))

    #print(gain_dict, time_dict, obsv_dict)
    print(obsv_sigma_dict)

    pdf = PdfPages(f'{filepath}/gain_timedep_{channel}.pdf')
    for key in gain_dict:
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.plot(time_dict[key], gain_dict[key], label='gain',color='tab:blue')
        ax2.plot(time_dict[key], obsv_dict[key], label='obs hv',color='tab:orange')
        ax2.fill_between(time_dict[key],np.array(obsv_dict[key])-np.array(obsv_sigma_dict[key]),np.array(obsv_dict[key])+np.array(obsv_sigma_dict[key]),color="tab:orange",alpha=0.5)
        plt.title(f'Gain for {key} V')
        handler1, label1 = ax1.get_legend_handles_labels()
        handler2, label2 = ax2.get_legend_handles_labels()
        ax1.legend(handler1+handler2, label1+label2)
        meangain = np.mean(np.array(gain_dict[key]))
        meanhv = np.mean(np.array(obsv_dict[key]))
        ax1.set_ylim(0.8*meangain,1.2*meangain)
        ax2.set_ylim(meanhv-50, meanhv+50)
        pdf.savefig()
        plt.clf()
    pdf.close()

if __name__ == '__main__':
    cli()
