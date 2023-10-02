import matplotlib.pyplot as plt
import numpy as np
import tables
import os, sys, time
import click
from tqdm import tqdm
import gc
from matplotlib.backends.backend_pdf import PdfPages

basehv = 1500

# from the instability region data 
fit_max = 1210
fit_min = 1160
popt = np.array([-2.12467457e-03,  7.61361316e+00, -9.09340030e+03,  3.61995958e+06])

def tripol(x, a, b, c, d):
    return a*x**3 + b*x**2 + c*x + d

def calculate(nevents,simple=False,out=None):
    with tables.open_file('../../../results/SPELED/instab_test/old/Run5/raw/data_ch0.hdf') as f:
        data = f.get_node('/data')
        charges = data.col('charge')
        setvs = data.col('setv')
        hvvs = data.col('hvv')
        hvis = data.col('hvi')
    
    print(setvs)
    print(len(charges), len(setvs), len(hvvs), len(hvis))
    if nevents > len(charges[0]):
        print('WARNING: The number of events is set to {len(charges[0])} (maximum)')
        nevents = len(charges[0])
    
    charge_data = []
    hvv_data = []
    hvi_data = []
    if out is not None:
        suffix = out
    else:
        suffix = ""
    prefix = f'./plots/{out}'
    os.makedirs(prefix)
    pdf = PdfPages(f'{prefix}/HV_fluctuation_PDF_{suffix}.pdf')
    for half_width in tqdm(np.arange(101)):

        hvflucx = np.linspace(fit_min,fit_max,2*half_width+1)
        if simple:
            hvflucy = np.ones(len(hvflucx))
        else:
            hvflucy = tripol(hvflucx, *popt)
        
        hv_width = np.arange(-half_width,half_width+1) 
        diffhv_array = []
        for hv,num in zip(hv_width,hvflucy):
            diffhv_array.extend([hv]*int(num))

        diffhv = np.mean(np.array(diffhv_array))
        if max(hv_width) + (basehv - diffhv) > 1600:
            break
        if min(hv_width) + (basehv - diffhv) < 1400:
            break

        hv_app = hv_width + int(basehv - diffhv)

        num_events = np.array([int(n/np.sum(hvflucy)*nevents) for n in hvflucy])
        
        plt.fill_between(hv_app,num_events,step='mid',alpha=0.4)
        plt.plot(hv_app,num_events,ds='steps-mid')
        plt.xlabel('Voltage [V]')
        plt.ylabel('Entries')
        plt.axvline(int(basehv - diffhv),ls=':',color='magenta')
        pdf.savefig()
        plt.clf()
        
        charge_data_ = []
        hvv_mean_ = 0
        hvv_std_ = 0
        hvi_mean_ = 0
        hvi_std_ = 0
        tot_events = 0

        for hv in hv_app:
            num_here_ = num_events[hv_app==hv][0]
            # charge
            charge_here_ = charges[setvs==hv]
            try: 
                charge_filtered = charge_here_[0][:num_here_]
            except: 
                if hv>min(hv_app):
                    charge_here_ = charges[setvs==(hv-1)]
                    try:
                        charge_filtered = charge_here_[0][:num_here_]
                    except:
                        charge_filtered = np.zeros(num_here_)
                else:
                    charge_filtered = np.zeros(num_here_)
            charge_data_.extend(charge_filtered)
            # hv reference
            if len(hvvs[setvs==hv])==0:
                if hv>min(hv_app):
                    hvv_here_ = np.mean(hvvs[setvs==(hv-1)])+1
                else:
                    hvv_here_ = 0
            else:
                hvv_here_ = np.mean(hvvs[setvs==hv])
            if len(hvis[setvs==hv])==0:
                if hv>min(hv_app):
                    hvi_here_ = np.mean(hvis[setvs==(hv-1)])
                else:
                    hvi_here_ = 0
            else:
                hvi_here_ = np.mean(hvis[setvs==hv])
            hvv_mean_ += hvv_here_ * num_here_ 
            hvv_std_ += hvv_here_**2 *num_here_ 
            hvi_mean_ += hvi_here_ * num_here_ 
            hvi_std_ += hvi_here_**2 *num_here_ 
            del charge_filtered
            if hvv_here_==0 * hvi_here_==0:
                continue
            tot_events += num_here_

        charge_data.append(np.array(charge_data_))
        hvv_data.append(np.array([hvv_mean_/tot_events,hvv_std_/tot_events-(hvv_mean_/tot_events)**2]))
        hvi_data.append(np.array([hvi_mean_/tot_events,hvi_std_/tot_events-(hvi_mean_/tot_events)**2]))
        
        del charge_data_
        del hvv_mean_, hvv_std_
        del hvi_mean_, hvi_std_
        del hv_app
        del num_events 
        del hvflucx
        del hvflucy

    del data, charges, setvs, hvvs, hvis
    
    pdf.close()

    setvs = np.array(np.zeros(len(charge_data))+basehv)
    hvvs = np.array(hvv_data)
    hvis = np.array(hvi_data)
    cr_xaxis = np.arange(len(charge_data))

    gc.collect()

    from qstamp_analyze import charge_analyze
    
    charge_analyze(charges=charge_data,
                   setvs = setvs,
                   hvvs = hvvs,
                   hvis = hvis,
                   filepath = prefix,
                   thzero = 0.32,
                   startv = 1300,
                   steps = 250,
                   channel = 0,
                   cr_xaxis = cr_xaxis,
                   out=out,
                   lingood=True,
                   fixedfitrange="1,2.5")
    
@click.command()
@click.option('--nevents',type=float,default=1e4)
@click.option('--simple',is_flag=True)
@click.option('--out',type=str,default=None)
def main(nevents,simple,out):
    calculate(nevents,simple,out)

if __name__ == '__main__':
    main()
