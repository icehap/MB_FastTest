import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.ticker as ticker
import tables 
import click
import os, sys
from scipy.signal import argrelmax 
from natsort import natsorted
from scipy.optimize import curve_fit

lws = [1,2,1,1,2,1,1,2,1,1,2,1] # downward bold

def fitfunc(x,a,b):
    return a*x**b

def fitfunck(x,a,b):
    return a*(x/1000)**b

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
@click.option('--gain',default=None)
@click.option('--lint',type=int,default=2)
def vscan(filepath,gain,lint):
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

    if gain is not None:
        ocom = 'PE'
        with open(f'{gain}/gainfitparams.txt') as f:
            params = list(map(float,(f.readline()).split(',')))
        factor = fitfunck(np.mean(hv),*params)*1.6/1.e7 
        #factor = 1.6 * float(gain)
        plt.ylabel('Observed Mean Charge [PE]')
    else:
        ocom = ''
        factor = 1
        plt.ylabel('Observed Mean Charge [pC]')

    for i in range(12):
        if len(ledbias[np.log2(ledmask)==i]) > 0:
            plt.plot(ledbias[np.log2(ledmask)==i],meancharge[np.log2(ledmask)==i]/factor,lw=lws[i],label=f'LED{i+1}',color=cm.brg(i/12),ls='--')

    plt.title(f'Ch{channel[0]}, HV {np.mean(hv):.1f} V')
    plt.xlabel('Intensity Setting (hex)')
    plt.legend(bbox_to_anchor=(1,1), loc='upper left')
    
    axes = plt.gca()
    axes.get_xaxis().set_major_locator(ticker.MultipleLocator(lint*16**2))
    axes.get_xaxis().set_major_formatter(ticker.FuncFormatter(lambda x, pos: '%x' % int(x)))
    
    plt.tight_layout()
    plt.savefig(f'{filepath}/LEDlumi{ocom}.pdf')
    plt.yscale('log')
    plt.tight_layout()
    plt.savefig(f'{filepath}/LEDlumi{ocom}_log.pdf',bbox_inches="tight")
    plt.show()

@cli.command()
@click.option('--filepath',type=str,required=True)
@click.option('--gain',default=None)
@click.option('--flat',default=None)
def vscan_merge(filepath,gain,flat):
    fig = plt.figure(figsize=(8,5))
    filenames = [f'{filepath}/Run{i+1}/raw/test.hdf5' for i in range(6)]
    print(filenames)

    if gain is not None:
        with open(f'{gain}/gainfitparams.txt') as f:
            params = list(map(float,(f.readline()).split(',')))
        #print(params)

    for i in range(len(filenames)):
        with tables.open_file(filenames[i]) as f:
            data = f.get_node('/data')
            charges = data.col('chargestamp')
            hvs = data.col('hv')
            ledmask = data.col('ledmask')
            ledbias = data.col('ledbias')
        if gain is not None:
            gain_eval = np.array([fitfunck(x,*params)*1.6/1.e7 for x in hvs])
        else: 
            gain_eval = np.array([1. for x in hvs])
        #print(gain, hvs)
        meanpe = np.mean(charges,axis=1)/gain_eval
        for ii in range(12):
            if len(ledbias[np.log2(ledmask)==ii]) > 0:
                thisledbias = ledbias[np.log2(ledmask)==ii]
                thismeanpe  = meanpe[np.log2(ledmask)==ii]
                plt.plot(thisledbias,thismeanpe,lw=lws[ii],color=cm.brg(ii/12),ls='--')

    dummy = []
    h1 = []
    for i in range(12):
        g, = plt.plot(dummy, dummy, color=cm.brg(i/12), ls='--', lw=lws[i], label=f'LED{i+1}')
        h1.append(g)

    if flat is not None:
        intensity, led = getFlat(flat)
        ocom = 'wflat'
        for i in range(12):
            plt.plot(intensity[led[i]>0], led[i][led[i]>0], color=cm.brg(i/12), lw=lws[i])
        plt.legend(bbox_to_anchor=(1,1), loc='upper left')
        g1, = plt.plot(dummy, dummy, color='black',ls='--',label='D-Egg')
        g2, = plt.plot(dummy, dummy, color='black',label='FLAT')
        h2 = [g1, g2]
        lab1 = [h.get_label() for h in h1]
        lab2 = [h.get_label() for h in h2]
        leg1 = plt.legend(h1, lab1, bbox_to_anchor=(1.02,1), borderaxespad=0, loc='upper left')
        leg2 = plt.legend(h2, lab2, bbox_to_anchor=(1.02,0), borderaxespad=0, loc='lower left')
        plt.gca().add_artist(leg1)
    else:
        ocom = ''
        plt.legend(bbox_to_anchor=(1,1), loc='upper left')

    plt.title('LED full range measurement')
    plt.xlabel('Intensity Setting (hex)')
    if gain is not None: 
        plt.ylabel('Observed Mean Photo-Electrons [PE]')
    else:
        plt.ylabel('Observed Mean Charge [pC]')
    
    axes = plt.gca()
    axes.get_xaxis().set_major_locator(ticker.MultipleLocator(2*16**3))
    axes.get_xaxis().set_major_formatter(ticker.FuncFormatter(lambda x, pos: '%x' % int(x)))
    
    plt.yscale('log')
    #plt.xlim(0x5500,0xa000)
    plt.grid()
    plt.tight_layout()
    if gain is not None:
        plt.savefig(f'{filepath}/LEDwhole{ocom}_log.pdf',bbox_inches='tight')
    else:
        plt.savefig(f'{filepath}/LEDwholeRAW{ocom}_log.pdf',bbox_inches='tight')
    plt.show()


@cli.command()
@click.option('--filepath',type=str,required=True)
def gainmeas(filepath):
    filename = f'{filepath}/raw/test.hdf5'
    f = tables.open_file(filename)
    data = f.get_node('/data')
    charges = data.col('chargestamp')
    hvs = data.col('hv')
    f.close()
    
    gains = []
    maxid = 0
    for i in range(len(charges)):
        hist, bins = np.histogram(charges[i],bins=210,range=(-0.5,10))
        def gaussian(x, amp, mean, sigma): 
            return amp * np.exp( -(x-mean)**2 / (2*sigma**2))

        bin_width = np.diff(bins)
        bin_centers = bins[:-1] + bin_width /2 
        popt, _ = curve_fit(gaussian, bin_centers, hist, p0 = [1.,0.,1.])
        #print(popt)

        x_fit = np.linspace(bins[0], bins[-1], 10000)

        hist_subt = np.array([hist[j] - gaussian(bin_centers[j],*popt) for j in range(len(hist))])
        prevmaxid = maxid
        maxid = int(np.argmax(hist_subt[bin_centers>bin_centers[maxid]])+maxid)
        maxid2 = argrelmax(hist_subt,order=100)
        gopt, _ = curve_fit(gaussian, bin_centers[prevmaxid:], hist_subt[prevmaxid:], p0 = [1.,bin_centers[maxid],1.])
        print(maxid, gopt[1])
        #gain = (bin_centers[maxid]-popt[1])/1.6 * 1.e7
        gain = (gopt[1]-popt[1])/1.6 * 1.e7
        #print(gain)
        gains.append(gain)

        plt.step(bin_centers, hist)
        plt.plot(x_fit, gaussian(x_fit,*popt))
        plt.plot(x_fit, gaussian(x_fit,*gopt))
        #plt.axvline(bin_centers[maxid],color='magenta')
        plt.axvline(gopt[1],color='magenta',lw=1,ls=':')
        plt.yscale('log')
        plt.ylim(0.1, max(hist)*10)
        plt.tight_layout()
        plt.savefig(f'{filepath}/plots/fit_{i}.pdf',bbox_inches='tight')
        plt.show()

    gains = np.array(gains)
    gpopt, _ = curve_fit(fitfunc,hvs[hvs>1200]/1000,gains[hvs>1200])

    with open(f'{filepath}/gainfitparams.txt',mode='w') as f:
        f.write(f'{gpopt[0]},{gpopt[1]}\n')

    plt.plot(hvs, gains,marker='o',lw=0)
    xdata = np.linspace(900,1800,10000)
    plt.plot(xdata, fitfunck(xdata,*gpopt))
    plt.xlabel('Applied HV [V]')
    plt.ylabel('Gain')
    plt.yscale('log')
    plt.grid()
    plt.tight_layout()
    plt.savefig(f'{filepath}/gainfit.pdf',bbox_inches='tight')
    plt.show()

@cli.command()
@click.option('--gainfile',type=str,required=True)
@click.option('--target',type=float,required=True)
def eval_votg(gainfile,target):
    with open(gainfile) as f:
        params = list(map(float,(f.readline()).split(',')))
    print(f'HV: {(target/params[0])**(1/params[1])*1000:.1f} V')


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
    plt.tight_layout()
    plt.savefig(f'{filepath}/LEDlumi_log.pdf')
    plt.show()

def getFlat(filename):
    with tables.open_file(filename) as f:
        data = f.get_node('/df')
        intensity = np.array([i[0] for i in data['block1_values']])
        led = np.array([[ii[np.array([i.decode() for i in data['block0_items']])==f'LED{j+1}'][0] for ii in data['block0_values']] for j in range(12)])
    return intensity, led

if __name__=='__main__':
    cli()
