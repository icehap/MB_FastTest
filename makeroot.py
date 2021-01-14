#!/usr/bin/env python3

import tables
import os
import sys
import gc
import numpy as np
from ROOT import TFile, TH1D, gROOT, gDirectory, TGraphErrors, TCanvas
from argparse import ArgumentParser
from tqdm import tqdm

def main():
    args = parser()

    filename = args.filename

    os.system('mkdir -p rootfiles')
    os.system('mkdir -p plots')

    f = tables.open_file(filename)
    print(f"Successfully opened file: {filename}.")

    data = f.get_node('/data')
    print("Read /data")

    event_ids = getDataCol('event_id',data)
    waveforms = getDataCol('waveform',data)
    times = getDataCol('time',data)
    timestamps = getDatCol('timestamp',data)
    thresFlags = getDataCol('thresholdFlags',data)
    i_1V1  = getDataCol('i_1V1' ,data)
    i_1V35 = getDataCol('i_1V35',data)
    i_1V8  = getDataCol('i_1V8' ,data)
    i_2V5  = getDataCol('i_2V5' ,data)
    i_3V3  = getDataCol('i_3V3' ,data)
    v_1V1  = getDataCol('v_1V1' ,data)
    v_1V35 = getDataCol('v_1V35',data)
    v_1V8  = getDataCol('v_1V8' ,data)
    v_2V5  = getDataCol('v_2V5' ,data)
    v_3V3  = getDataCol('v_3V3' ,data)

    nsamples = len(waveforms[0])
    fq = np.linspace(0,240,nsamples)

    gmean = np.mean(waveforms[0])
    globalmean = np.mean(waveforms)
    print(np.mean(waveforms[0]))

    c = TCanvas("c","c",800,600)
    c.Draw()
    c.SetGrid()

    of = TFile('rootfiles/{0}.root'.format(filename.split('.h',1)[0]),"RECREATE")

    h    = TH1D('qdist','qdist;ADC count;Entry',500,-100,900)
    hpk  = TH1D('peak','peak;ADC count;Entry',500,-100,900)
    havg = TH1D('avgwf','Averaged Waveform;Sampling Bin;ADC count',nsamples,0,nsamples)
    havgfft = TH1D('avgfft','FFT Averaged Waveform;Frequency [MHz];Amplitude [LSB]',int(len(fq)/2)+1,0,120+240/(nsamples-1))
    hifft = TH1D('Subtwf','Averaged Waveform;Sampling Bin;ADC count',nsamples,0,nsamples)
    hsfft = TH1D('Subtfft','FFT Averaged Waveform;Frequency [MHz];Amplitude [LSB]',int(len(fq)/2)+1,0,120+240/(nsamples-1)) 
    hsspe = TH1D('qdist_subt','qdist_subt;ADC count;Entry',500,-100,900)
    hmax  = TH1D('hmax','hmax;ADC count;Entry',500,-100,900)
    bsfluc = TH1D('bsfluc','bsfluc;ADC count;Entry',100, int(globalmean)-50, int(globalmean)+50)
    bsshift = TGraphErrors()
    bsshift.SetName('bsshift')
    bsshift.SetTitle('bsshift;Event Number;Baseline [LSB]')
    nrshift = TGraphErrors()
    nrshift.SetName('nrshift')
    nrshift.SetTitle('NoiseRateShift;Event Number;Noise Rate [Hz]')
    rmsshift = TGraphErrors()
    rmsshift.SetName('rmsshift')
    rmsshift.SetTitle('RMSNoiseShift;Event Number;RMS Noise [LSB]')
    rmstime = TGraphErrors()
    rmstime.SetName('rmstime')
    rmstime.SetTitle('rmstime;Unix time [s];RMS Noise [LSB]')
    powerc = TGraphErrors()
    powerc.SetName('powerc')
    powerc.SetTitle('powerc;Event Number;Power Consumption [W]')
    h_powerc = TH1D('h_powerc','h_powerc;Power Consumption [W];Entry',100,0,5)
    
    winmin = args.minimum
    winmax = args.minimum + args.window
    bsstart = args.baselineEst

    print (f'Total #Events: {len(waveforms)}')
    print (f'Setting... Window [{winmin}:{winmax}] and Pedestal start from {bsstart}.\n')

    topdir = gDirectory.GetDirectory(gDirectory.GetPath())
    subdir = topdir.mkdir("Waveforms")
    subdir2 = topdir.mkdir("FFT")
    subdir3 = topdir.mkdir("proj")
    thrdir = topdir.mkdir("thresFlags")

    fltwfs = []
    starttimestamp = timestamps[0]

    procN = len(waveforms)
    if args.nevents > 0: 
        procN = args.nevents

    for i in tqdm(range(procN)):
        if i < args.nskip: 
            continue

        waveform = waveforms[i]
        timestamp = timestamps[i]

        bsfluc.Fill(np.mean(waveform))
        n = bsshift.GetN()
        bsshift.Set(n+1)
        bsshift.SetPoint(n, i, np.mean(waveform))
        bsshift.SetPointError(n, 0, np.std(waveform))

        n = rmsshift.GetN()
        rmsshift.Set(n+1)
        rmsshift.SetPoint(n, i, np.std(waveform))
        rmsshift.SetPointError(n, 0, 0)
        
        hmax.Fill(np.max(waveform)-np.mean(waveform))

        timeinterval = ((timestamp - starttimestamp - i*nsamples)/240.e6 - i * 0.501)
        nr = 0 
        nrerr = 0
        if timeinterval > 0: 
            nr = (i+1)/timeinterval 
            nrerr = np.sqrt(i+1)/timeinterval
        n = nrshift.GetN()
        nrshift.Set(n+1)
        nrshift.SetPoint(n, i, nr) 
        nrshift.SetPointError(n, 0, nrerr)

        # FFT & IFFT ###
        F_abs_amp = doFFT(waveform)

        F = np.fft.fft(waveform)
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
        if args.fixbs: 
            baseline_mean = globalmean

        center = int(baseline_mean)
        proj = TH1D(f'proj{i}',f'Projection waveform{i};ADC count;Entry',300,center-150,center+150)
        selected = waveform[waveform < np.mean(waveform) + 10]
        for j in range(len(selected)):
            proj.Fill(selected[j])
        #proj.Fit("gaus")
        #if len(selected) > 0:
        #    f = proj.GetFunction('gaus')
        #    norm = f.GetParameter(0)
        #    mean = f.GetParameter(1)
        #    sigma = f.GetParameter(2)

        reduced_waveform = waveform - baseline_mean
        scale = (nsamples-bsstart)/(winmax-winmin)
        #h.Fill(sum(waveform[winmin:winmax])-sum(waveform[bsstart:nsamples])/scale)
        h.Fill(sum(reduced_waveform[winmin:winmax]))

        hsspe.Fill(np.sum(F2_ifft_real[winmin:winmax])-baseline_mean*(winmax-winmin))

        hpk.Fill(max(waveform[winmin:winmax])-np.mean(waveform[bsstart:nsamples]))

        hfft = TH1D(f'FFT{i}','FFT{i};Frequency [MHz];Amplitude [LSB]',int(len(fq)/2)+1,0,120+240/(nsamples-1))
        hfft2 = TH1D(f'FFT2{i}','FFT2{i};Frequency [MHz];Amplitude [LSB]',int(len(fq)/2)+1,0,120+240/(nsamples-1))
        for j in range(int(len(F_abs_amp)/2.+1)):
            hfft.Fill(fq[j],F_abs_amp[j])
            hfft2.Fill(fq[j],F2_abs_amp[j])

        h2 = TH1D(f'w{i}','Waveform{i};Sampling Bin;ADC count',nsamples,0,nsamples)
        for j in range(len(waveform)):
            h2.Fill(j,waveform[j])
        #h2.Draw("hist")

        #if np.max(F2_abs_amp[1:int(len(F2_abs_amp)/2.+1)]) > 0.5:
        #    c.SetLogy(0)
        #    h2.SetLineColor(4)
        #    h2.Draw("hist")
        #    c.Print(f"plots/w{i}.pdf(")
        #    c.SetLogy(1)
        #    hfft.SetLineColor(4)
        #    hfft.Draw("hist")
        #    c.Print(f"plots/w{i}.pdf)")

        htot = TH1D(f'thresflags{i}','ThresholdFlags{i};Sampling Bin;Threshold Flag',nsamples,0,nsamples)
        for j in range(len(thresFlags[i])):
            htot.Fill(j,thresFlags[i][j])

        if max(waveform) - baseline_mean < args.threshold:
            continue

        fltwfs.append(waveform)

        if args.silent: 
            del hfft
            del hfft2
            del h2
            del htot
            del proj 
            del waveform 
            del timestamp
            del F
            del F2
            gc.collect()
            continue

        subdir2.cd()
        hfft.Write()
        
        subdir.cd()
        h2.Write()

        subdir3.cd()
        proj.Write()

        thrdir.cd()
        htot.Write()

    print('')

    for i in range(len(i_1V1)): 
        internal_power = v_1V1[i]*i_1V1[i] + v_1V35[i]*i_1V35[i] + v_1V8[i]*i_1V8[i] + v_2V5[i]*i_2V5[i] + v_3V3[i]*i_3V3[i]
        n = powerc.GetN()
        powerc.Set(n+1)
        powerc.SetPoint(n, i, internal_power*1e-3)
        powerc.SetPointError(n, 0, 0)
        h_powerc.Fill(internal_power*1e-3)

    avgfltwfs = np.mean(fltwfs, axis=0)
    for i in range(len(avgfltwfs)): 
        havg.Fill(i,avgfltwfs[i])
    
    Favg_abs_amp = doFFT(avgfltwfs) 

    Favg = np.fft.fft(avgfltwfs)
    Favg2 = np.copy(Favg)
    Favg2[(fq>59) & (fq<61)] = 0
    Favg2[(fq>119) & (fq<121)] = 0
    Favg2[(fq>179) & (fq<181)] = 0

    Favg2_abs = np.abs(Favg2)
    Favg2_abs_amp = Favg2_abs / len(avgfltwfs) * 2
    Favg2_abs_amp[0] = Favg_abs_amp[0] / 2

    Favg2_ifft = np.fft.ifft(Favg2)
    Favg2_ifft_real = Favg2_ifft.real

    for i in range(int(len(Favg_abs_amp)/2.+1)):
        havgfft.Fill(fq[i],Favg_abs_amp[i])

    for i in range(int(len(Favg2_abs_amp)/2.+1)):
        hsfft.Fill(fq[i],Favg2_abs_amp[i])

    for i in range(len(Favg2_ifft_real)): 
        hifft.Fill(i, Favg2_ifft_real[i])

    topdir.cd()
    h.Write()
    hpk.Write()
    havg.Write()
    havgfft.Write()
    hsfft.Write()
    hifft.Write()
    hsspe.Write()
    hmax.Write()
    bsfluc.Write()
    bsshift.Write()
    nrshift.Write()
    rmsshift.Write()
    powerc.Write()
    h_powerc.Write()

    of.Close()
    f.close()

def doFFT(wf):
    F = np.fft.fft(wf)
    F_abs = np.abs(F)
    F_abs_amp = F_abs / len(wf) * 2
    F_abs_amp[0] = F_abs_amp[0] / 2
    return F_abs_amp 

def getDataCol(colname, hdfnode): 
    try: 
        coldata = hdfnode.col(colname)
    except:
        coldata = np.array([])
        print("Warning: Unabled to read {colname}.")
    else: 
        print(f"Read column: {colname}.")
    return coldata

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
    argparser.add_argument('-s','--silent', action='store_false')
    argparser.add_argument('-n','--nevents', default=-1, type=int, help='Number of process events.')
    argparser.add_argument('--nskip', default=-1, type=int, help='Number of skipping events. Should be larger than --nevents.')
    argparser.add_argument('--fixbs', action='store_true')

    return argparser.parse_args()


if __name__ == '__main__':
    gROOT.SetStyle("ATLAS")

    main()

