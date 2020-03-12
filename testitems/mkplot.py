import matplotlib.pyplot as plt
import numpy as np
import tables
import sys
import os
import glob
from natsort import natsorted

def mkplot(path):
    plt.rcParams['font.family'] = 'Liberation Sans'
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
    plt.rcParams['grid.color'] = 'gray'
    plt.rcParams['grid.linewidth'] = 0.4
    plt.rcParams['grid.linestyle'] = ':'
    plt.rcParams['legend.fancybox'] = False
    plt.rcParams['figure.subplot.right'] = 0.95
    plt.rcParams['figure.subplot.top'] = 0.95


    plt.ion()
    plt.show()

    # Noise RMS Distribution 
    fig = plt.figure()
    plt.xlabel("Mean [LSB]", ha='right', x=1.0)
    plt.ylabel("Noise RMS [LSB]", ha='right', y=1.0)

    filenames = []

    pathdata = path + '/*ch0*.hdf5'
    filenames = glob.glob(pathdata)
    x0, y0, yerr0, minFFT0 = mkDataSet(natsorted(filenames))
    plt.errorbar(x0,y0,yerr0,capsize=2,fmt='o',ms=5,ecolor='blue',markeredgecolor='blue',color='w')
    plt.plot(x0,y0,color='blue',label='Ch0')
    
    pathdata = path + '/*ch1*.hdf5'
    filenames = glob.glob(pathdata)
    x1, y1, yerr1, minFFT1 = mkDataSet(natsorted(filenames))
    plt.errorbar(x1,y1,yerr1,capsize=2,fmt='o',ms=5,ecolor='red',markeredgecolor='red',color='w')
    plt.plot(x1,y1,color='red',label='Ch1')

    plt.legend()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.001)
    plt.savefig(path+'/DACscanPlot.pdf')

    # FFT for ch0
    fig = plt.figure()
    plt.xlabel("Frequency [MHz]", ha='right', x=1.0)
    plt.ylabel("Amplitude [LSB]", ha='right', y=1.0)
    plt.yscale('log')
    plt.plot(minFFT0[0],minFFT0[1],color='blue',label='Ch0')
    plt.xlim(0,120)
    plt.legend()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.001)
    plt.savefig(path+'/DACscanFFT0Plot.pdf')

    # FFT for ch1 
    fig = plt.figure()
    plt.xlabel("Frequency [MHz]", ha='right', x=1.0)
    plt.ylabel("Amplitude [LSB]", ha='right', y=1.0)
    plt.yscale('log')
    plt.plot(minFFT1[0],minFFT1[1],color='red',label='Ch1')
    plt.xlim(0,120)
    plt.legend()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.001)
    plt.savefig(path+'/DACscanFFT1Plot.pdf')

    
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

    return x, y, yerr, minFFT
    

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
    fq = np.linspace(0,240,len(waveform))

    F = np.fft.fft(waveform)
    F_abs = np.abs(F)
    F_abs_amp = F_abs / len(waveform) * 2
    F_abs_amp[0] = F_abs_amp[0] / 2

    F2 = np.copy(F)
    fc = 60
    df = 2
    F2[(fq>fc-df) & (fq<fc+df)] = 0
    F2[(fq>2*fc-df) & (fq<2*fc+df)] = 0
    F2[(fq>240-fc-df) & (fq<240-fc+df)] = 0
    F2_abs = np.abs(F2)
    F2_abs_amp = F2_abs / len(waveform) *2 
    F2_abs_amp[0] = F2_abs_amp[0] / 2

    F2_ifft = np.fft.ifft(F2)
    F2_ifft_real = F2_ifft.real

    return [fq[:int(len(waveform)/2)+1], F_abs_amp[:int(len(waveform)/2)+1], F2_abs_amp[:int(len(waveform)/2)+1], F2_ifft_real]


if __name__ == "__main__":
    mkplot(sys.argv[1])
