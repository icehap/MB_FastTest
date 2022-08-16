#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
import os, sys
import numpy as np
import scope 
import time 
from addparser_iceboot import AddParser 
import matplotlib.pyplot as plt 
from sensorcheck import monitorcurrent 
from loadFPGA import loadFPGA
from utils import pathSetting

def main(parser): 
    (options, args) = parser.parse_args()

    nevents = int(options.nevents)
    path = pathSetting(options,'IMON',True)

    loadFPGA(parser)

    session = startIcebootSession(parser)
    v = monitorcurrent(session, nevents, waittime=0.2)
    np.save(f'{path}/mb_imon.npy',v)
    
    maxvalue = 100

    if not options.b:
        plt.ion()

    fig = plt.figure(figsize=(8.5,4.8))
    x = np.arange(nevents)
    for i in range(len(v)):
        if nevents > maxvalue:
            plt.plot(x[:maxvalue],v[i][:maxvalue],marker='o',label=f'Ch-{i}')
        else:
            plt.plot(x,v[i],marker='o',label=f'Ch-{i}')
    plt.xlabel('# of sampling')
    plt.ylabel('Monitored Current [mA]')
    plt.legend()
    plt.ylim(0,1250)
    plt.tight_layout()
    plt.savefig(f'{path}/currentmonitor.pdf')
    if options.b:
        plt.show()
    else:
        plt.draw()
    
    names = ['+1V1','+1V35','+1V8','+2V5','+3V3']  
    
    fig = plt.figure(figsize=(8.5,4.8))
    for i in range(len(v)):
        plt.hist(v[i],bins=200,range=(0,1200),histtype='step',label=f'Ch-{i} ({names[i]})')
    plt.xlabel('Monitored Current [mA]')
    plt.ylabel('Entry')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{path}/currentmonitor_hist.pdf')
    if options.b:
        plt.show()
    else:
        plt.draw()

    fig = plt.figure(figsize=(8.5,4.8))
    x = np.arange(int(nevents/10))
    for i in range(len(v)):
        vmean = [np.mean(v[i][10*j:10*(j+1)-1]) for j in range(int(nevents/10))]
        plt.plot(x,vmean,marker='o',label=f'Ch-{i}')
    plt.xlabel('# of sampling')
    plt.ylabel('10-averaged Monitored Current [mA]')
    plt.legend()
    plt.ylim(0,1250)
    plt.tight_layout()
    plt.savefig(f'{path}/currentmonitor_avg.pdf')
    if options.b:
        plt.show()
    else:
        plt.draw()

    fig = plt.figure(figsize=(8.5,4.8))
    for i in range(len(v)):
        vmean = [np.mean(v[i][10*j:10*(j+1)-1]) for j in range(int(nevents/10))]
        plt.hist(vmean,bins=200,range=(0,1200),histtype='step',label=f'Ch-{i} ({names[i]})')
    plt.xlabel('10-averaged Monitored Current [mA]')
    plt.ylabel('Entry')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{path}/currentmonitor_avg_hist.pdf')
    if options.b:
        plt.show()
    else:
        plt.draw()

    
if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)
    (options, args) = parser.parse_args()
    if not options.b:
        import matplotlib as mpl
        mpl.use('PDF')

    main(parser)
