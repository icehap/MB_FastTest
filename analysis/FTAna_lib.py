import numpy as np

def wfFFT(waveform, isRaw=True):
    F = np.fft.fft(waveform)
    F_abs = np.abs(F)
    if isRaw:
        return F
    else:
        F_abs_amp = getAbsFFT(F,len(waveform))
        return F_abs_amp

def wfFFTfilter(waveform, freqcut=60, cutwindow=2, isRaw=True): # unit: MHz
    fq = np.linspace(0,240,len(waveform))
    F = np.fft.fft(waveform)
    Fout = FFTfilter(F, fq, freqcut, cutwindow)
    F_abs_amp = getAbsFFT(F, len(waveform))
    if isRaw: 
        return Fout
    else: 
        return F_abs_amp

def FFTfilter(F,fq,freqcut,cutwindow):
    F[(fq>freqcut-cutwindow) & (fq<freqcut+cutwindow)] = 0
    F[(fq>2*freqcut-cutwindow) & (fq<2*freqcut+cutwindow)] = 0
    F[(fq>240-freqcut-cutwindow) & (fq<240-freqcut+cutwindow)] = 0
    return F

def wfIFFT(fft):
    F_ifft = np.fft.ifft(fft)
    F_ifft_real = F_ifft.real
    return F_ifft_real 

def getAbsFFT(F,normfactor):
    F_abs = np.abs(F)
    F_abs_amp = F_abs / normfactor * 2
    F_abs_amp[0] = F_abs_amp[0] / 2
    return F_abs_amp

def getData(filename):
    f = tables.open_file(filename)
    data = f.get_node('/data')
    return data

