#!/usr/bin/env python3

import tables
import os
import sys
import numpy as np
from ROOT import TFile, TH1D, gROOT, gDirectory
from argparse import ArgumentParser
from tqdm import tqdm

def main():
    args = parser()

    filename = args.filename

    os.system('mkdir -p rootfiles')

    f = tables.open_file(filename)

    data = f.get_node('/data')
    event_ids = data.col('event_id')
    times = data.col('time')
    waveforms = data.col('waveform')

    nsamples = len(waveforms[0])
    fq = np.linspace(0,240,nsamples)

    gmean = np.mean(waveforms[0])
    print(np.mean(waveforms[0]))

    of = TFile('rootfiles/{0}.root'.format(filename.split('.h',1)[0]),"RECREATE")

    h    = TH1D('qdist','qdist;ADC count;Entry',500,-100,900)
    hpk  = TH1D('peak','peak;ADC count;Entry',500,-100,900)
    havg = TH1D('avgwf','Averaged Waveform;Sampling Bin;ADC count',nsamples,0,nsamples)
    havgfft = TH1D('avgfft','FFT Averaged Waveform;Frequency [MHz];Amplitude [LSB]',int(len(fq)/2)+1,0,120+240/(nsamples-1))
    
    winmin = args.minimum
    winmax = args.minimum + args.window
    bsstart = args.baselineEst

    print (f'Total #Events: {len(waveforms)}')
    print (f'Setting... Window [{winmin}:{winmax}] and Pedestal start from {bsstart}.\n')

    topdir = gDirectory.GetDirectory(gDirectory.GetPath())
    subdir = topdir.mkdir("Waveforms")
    subdir2 = topdir.mkdir("FFT")
    subdir3 = topdir.mkdir("proj")

    fltwfs = []

    for i in tqdm(range(len(waveforms))):
        waveform = waveforms[i]

        # FFT & IFFT ###
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
        F2_abs_amp = F2_abs / len(waveform) * 2
        F2_abs_amp[0] = F_abs_amp[0] / 2

        F2_ifft = np.fft.ifft(F2)
        F2_ifft_real = F2_ifft.real
        ######

        baseline_mean = np.mean(waveform[bsstart:nsamples])

        center = int(baseline_mean)
        proj = TH1D(f'proj{i}','Projection waveform;ADC count;Entry',300,center-150,center+150)
        selected = waveform[waveform < np.mean(waveform) + 10]
        for j in range(len(selected)):
            proj.Fill(selected[j])
        proj.Fit("gaus")
        if len(selected) > 0:
            f = proj.GetFunction('gaus')
            norm = f.GetParameter(0)
            mean = f.GetParameter(1)
            sigma = f.GetParameter(2)

        reduced_waveform = waveform - mean
        scale = (nsamples-bsstart)/(winmax-winmin)
        #h.Fill(sum(waveform[winmin:winmax])-sum(waveform[bsstart:nsamples])/scale)
        h.Fill(sum(reduced_waveform[winmin:winmax]))

        hpk.Fill(max(waveform[winmin:winmax])-np.mean(waveform[bsstart:nsamples]))

        hfft = TH1D(f'FFT{i}','FFT;Frequency [MHz];Amplitude [LSB]',int(len(fq)/2)+1,0,120+240/(nsamples-1))
        for j in range(int(len(F_abs_amp)/2.+1)):
            hfft.Fill(fq[j],F_abs_amp[j])
        #hfft.Draw("hist")

        h2 = TH1D(f'w{i}','Waveform;Sampling Bin;ADC count',nsamples,0,nsamples)
        for j in range(len(waveform)):
            h2.Fill(j,waveform[j])
        #h2.Draw("hist")


        if max(waveform) - np.mean(waveform[bsstart:nsamples]) < args.threshold:
            continue

        fltwfs.append(waveform)

        subdir2.cd()
        hfft.Write()
        
        subdir.cd()
        h2.Write()

        subdir3.cd()
        proj.Write()

    print('')

    avgfltwfs = np.mean(fltwfs, axis=0)
    for i in range(len(avgfltwfs)): 
        havg.Fill(i,avgfltwfs[i])
    
    Favg = np.fft.fft(avgfltwfs)
    Favg_abs = np.abs(Favg)
    Favg_abs_amp = Favg_abs / len(avgfltwfs) * 2 
    Favg_abs_amp[0] = Favg_abs_amp[0] / 2 

    Favg2 = np.copy(Favg)
    Favg2[(fq>59) & (fq<61)] = 0
    Favg2[(fq>119) & (fq<121)] = 0
    Favg2[(fq>179) & (fq<181)] = 0

    Favg2_ifft = np.fft.ifft(Favg2)
    Favg2_ifft_real = Favg2_ifft.real

    for i in range(int(len(Favg_abs_amp)/2.+1)):
        havgfft.Fill(fq[i],Favg_abs_amp[i])

    topdir.cd()
    h.Write()
    hpk.Write()
    havg.Write()
    havgfft.Write()

    of.Close()


def parser():
    argparser = ArgumentParser()
    argparser.add_argument('filename', help='Input file name.')
    argparser.add_argument('-t', '--threshold', 
                           type=float, default=20, 
                           help='Threshold for saving waveform')
    argparser.add_argument('-mi','--minimum', 
                           type=int, default=90, 
                           help='Minimum value of the integration window (sampling bin number).')
    argparser.add_argument('-win', '--window', 
                           type=int, default=20,
                           help='Window size. ')
    argparser.add_argument('-bs', '--baselineEst', 
                           type=int, default=160, 
                           help='Starting point of the window to evaluate the baseline value. ')

    return argparser.parse_args()


if __name__ == '__main__':
    gROOT.SetStyle("ATLAS")

    main()

