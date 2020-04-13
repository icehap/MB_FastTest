import matplotlib.pyplot as plt
import numpy as np
import tables
import sys
import os
import glob
from natsort import natsorted

def mkplot(path):
    plotSetting(plt)

    plt.ion()
    plt.show()

    # Noise RMS Distribution 
    fig = plt.figure()
    plt.xlabel("Baseline Mean [LSB]", ha='right', x=1.0)
    plt.ylabel("Noise RMS [LSB]", ha='right', y=1.0)

    filenames = []

    chcolors = ['b','r']
    ydata = []
    minFFTs = []
    maxFFTs = []

    plt.axhline(2.5,ls='-.', color='magenta',zorder=0)

    for channel in range(2):
        pathdata = path + '/dacscan*ch'+ str(channel) +'*.hdf5'
        filenames = glob.glob(pathdata)
        x, y, yerr, minFFT, maxFFT = mkDataSet(natsorted(filenames))
        plt.errorbar(x,y,yerr,capsize=2,marker='o',ms=5,ls='solid',color=chcolors[channel],label=f'Ch{channel}',zorder=channel+1)
        ydata.append(y)
        minFFTs.append(minFFT)
        maxFFTs.append(maxFFT)
    
    ymax = 8
    if ymax < max(y)+max(yerr): 
        ymax = (max(y)+max(yerr))+1
    plt.ylim(0,ymax)
    plt.legend()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.001)
    plt.savefig(path+'/DACscanPlot.pdf')

    y0 = ydata[0]
    y1 = ydata[1]


    # FFT plot for each channel
    for channel in range(2):
        minFFT = minFFTs[channel]
        fig = plt.figure()
        plt.xlabel("Frequency [MHz]", ha='right', x=1.0)
        plt.ylabel("Apmlitude [LSB]", ha='right', y=1.0)
        plt.yscale('log')
        plt.plot(minFFT[0],minFFT[1],color=chcolors[channel],label=f'Ch{channel}')
        plt.xlim(0,120)
        plt.legend()
        fig.canvas.draw()
        fig.canvas.flush_events()
        plt.pause(0.001)
        plt.savefig(path+'/DACscanFFT'+str(channel)+'Plot.pdf')

    # Max FFT plot
    for channel in range(2):
        maxFFT = maxFFTs[channel]
        fig = plt.figure()
        plt.xlabel("Frequency [MHz]", ha='right', x=1.0)
        plt.ylabel("Apmlitude [LSB]", ha='right', y=1.0)
        plt.yscale('log')
        plt.plot(maxFFT[0],maxFFT[1],color=chcolors[channel],label=f'Ch{channel}')
        plt.xlim(0,120)
        plt.legend()
        fig.canvas.draw()
        fig.canvas.flush_events()
        plt.pause(0.001)
        plt.savefig(path+'/DACscanMFFT'+str(channel)+'Plot.pdf')

    retvalue = []
    
    miny0 = 1000
    miny1 = 1000
    if len(y0) > 0:
        miny0 = min(y0)
    if len(y1) > 0:
        miny1 = min(y1)

    minvalues = [miny0, miny1]

    if miny0 < 2.5:
        retvalue.append(1)
    else:
        retvalue.append(0)

    if miny1 < 2.5:
        retvalue.append(1)
    else:
        retvalue.append(0)

    return retvalue, minvalues

def mkDataSet(filenames):
    x = []
    y = []
    yerr = []
    FFTs = []

    for i in range(len(filenames)):
        x_1, y_1, yerr_1, FFTs_1 = getData(filenames[i])

        x.append(x_1)
        y.append(y_1)
        yerr.append(yerr_1)
        FFTs.append(FFTs_1)

    minFFT = FFTs[y.index(min(y))]
    maxFFT = FFTs[y.index(max(y))]

    return x, y, yerr, minFFT, maxFFT
    

def getData(filename):
    f = tables.open_file(filename)

    data = f.get_node('/data')
    event_ids = data.col('event_id')
    times = data.col('time')
    waveforms = data.col('waveform')

    nsamples = len(waveforms[0])
    meanwf = []
    rms = []
    for i in range(len(waveforms)): 
        meanwf.append(np.mean(waveforms[i]))
        rms.append(getArrRMS(waveforms[i]))

    FFTs = getFFTWF(np.mean(waveforms,axis=0))

    x = np.mean(meanwf)
    y = np.mean(rms)
    yerr = getArrRMS(np.array(rms))

    f.close()

    return x, y, yerr, FFTs

def getArrRMS(array):
    reducedArray = array - np.mean(array)
    rms  = np.sqrt(np.mean(np.square(reducedArray))-np.mean(reducedArray)**2)
    
    return rms

def getFFTWF(waveform):
    opf = 240 # operation frequency in MHz

    fq = np.linspace(0,opf,len(waveform))

    F = np.fft.fft(waveform)
    F_abs = np.abs(F)
    F_abs_amp = F_abs / len(waveform) * 2
    F_abs_amp[0] = F_abs_amp[0] / 2

    # FFT filtered 
    F2 = np.copy(F)
    fc = 60 # oscillation frequency
    df = 2
    F2[(fq>fc-df) & (fq<fc+df)] = 0
    F2[(fq>2*fc-df) & (fq<2*fc+df)] = 0
    F2[(fq>opf-fc-df) & (fq<opf-fc+df)] = 0
    F2_abs = np.abs(F2)
    F2_abs_amp = F2_abs / len(waveform) *2 
    F2_abs_amp[0] = F2_abs_amp[0] / 2

    F2_ifft = np.fft.ifft(F2)
    F2_ifft_real = F2_ifft.real

    return [fq[:int(len(waveform)/2)+1], F_abs_amp[:int(len(waveform)/2)+1], F2_abs_amp[:int(len(waveform)/2)+1], F2_ifft_real]

def plotSetting(plt):
    plt.rcParams['font.sans-serif'] = ['Arial','Liberation Sans']
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    plt.rcParams['xtick.top'] = True
    plt.rcParams['xtick.bottom'] = True
    plt.rcParams['ytick.left'] = True
    plt.rcParams['ytick.right'] = True
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.color'] = 'black'
    plt.rcParams['grid.linewidth'] = 0.8
    plt.rcParams['grid.linestyle'] = ':'
    plt.rcParams['legend.fancybox'] = False
    plt.rcParams['figure.subplot.right'] = 0.95
    plt.rcParams['figure.subplot.top'] = 0.95
    plt.rcParams['legend.edgecolor'] = 'white'
    plt.rcParams['legend.framealpha'] = 1.0
    plt.rcParams['xtick.minor.visible'] = True
    plt.rcParams['ytick.minor.visible'] = True
    plt.rcParams['xtick.minor.width'] = 0.8
    plt.rcParams['ytick.minor.width'] = 0.8
    plt.rcParams['xtick.major.size'] = 7
    plt.rcParams['ytick.major.size'] = 8
    plt.rcParams['xtick.minor.size'] = 3.5
    plt.rcParams['ytick.minor.size'] = 4
    plt.rcParams['axes.axisbelow'] = True
    plt.rcParams['figure.figsize'] = [6.4,4.0]


if __name__ == "__main__":
    mkplot(sys.argv[1])
