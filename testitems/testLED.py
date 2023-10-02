from iceboot.iceboot_session import getParser, startIcebootSession
from iceboot.test_waveform import parseTestWaveform, applyPatternSubtraction
import os, sys, time
import numpy as np
from addparser_iceboot import AddParser
import matplotlib.pyplot as plt
from mkplot import plotSetting
import signal

def doLEDflashing(session, freq=5000, bias=0x6000, flashermask=0xFFFF,debug=False):
    if debug:
        print('Now preparing for LED...')
    session.enableCalibrationPower()
    session.setCalibrationSlavePowerMask(2)
    session.enableCalibrationTrigger(freq)
    if debug:
        print('Now flashing LED...')
    #session.icmStartCalTrig(0,freq) # Unit 1: 17.06667[usec] 
    session.icmStartCalTrig()
    if debug:
        print(f'freq: {freq}')
    session.setFlasherBias(0x5310)
    session.setFlasherBias(bias)
    session.setFlasherMask(flashermask)

    time.sleep(1)

def setLEDon(numbers,doprint=True):
    rawnums = str(numbers).split(',')
    nums = np.array([])
    for i in rawnums:
        ii = i.split('-')
        if len(ii) > 1:
            can = np.array([int(ii[0]) + j for j in range(int(ii[1])-int(ii[0])+1)])
        else: 
            can = int(i)
        nums = np.append(nums,can).astype(int)
    if doprint:
        print(f'Turn on the following LEDs: {nums}')
    flashermask = 0
    led_configs = [0x0001,
                   0x0002,
                   0x0004,
                   0x0008,
                   0x0010,
                   0x0020,
                   0x0040,
                   0x0080,
                   0x0100,
                   0x0200,
                   0x0400,
                   0x0800]
                   
    for i in nums:
        flashermask += led_configs[i-1]

    return flashermask


def disableLEDflashing(session):
    session.icmStopCalTrig()

def main(parser):
    (options,args) = parser.parse_args()
    
    session = startIcebootSession(parser)

    # Number of samples must be divisible by 4
    nSamples = int((int(options.samples) / 4) * 4)
    if (nSamples < 16):
        print("Number of samples must be at least 16")
        sys.exit(1)

    session.setDEggConstReadout(int(options.channel), 1, int(nSamples))

    plt.ion()
    plt.show()
    fig = plt.figure(figsize=(6.4*(nSamples/256),4.8))
    ax = fig.add_subplot(111)
    plt.xlabel("Waveform Bin")
    plt.ylabel("ADC Count")
    line = None


    
    if options.hvv is not None:
        session.enableHV(int(options.channel))
        session.setDEggHV(int(options.channel),int(options.hvv))
        print('HV ramping... ')
        from tqdm import tqdm
        for x in tqdm(range(int(int(options.hvv)/50+1))):
            time.sleep(1)
        print(f'Done. Observed HV is {session.readSloADC_HVS_Voltage(int(options.channel))} V.')
    
    session.setDEggExtTrigSourceICM()

    if options.hbuf:
        print('Hit Buffer External Trigger Stream...')
        session.startDEggExternalHBufTrigStream(int(options.channel))
    else:
        print('Standard External Trigger Stream...')
        session.startDEggExternalTrigStream(int(options.channel))

    doLEDflashing(session,freq=options.freq,bias=options.intensity,flashermask=setLEDon(options.flashermask),debug=options.debug)

    index = 0
    xdata = np.arange(int(nSamples))
    sumwf = np.zeros(int(nSamples))

    # define signal handler to end the stream on CTRL-C
    def signal_handler(*args):
        print('\nEnding waveform stream...')
        session.endStream()
        session.icmStopCalTrig()
        print('Done')
        session.setDEggHV(int(options.channel), 0)
        session.disableHV(int(options.channel))
        avgwf = sumwf / index
        plt.clf()
        plt.plot(xdata,avgwf)
        plt.savefig('avgwf.pdf')
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    while (True):
        index = index + 1
        try:
            readout = parseTestWaveform(session.readWFMFromStream())
        except IOError:
            print('Timeout! Ending waveform stream and exiting')
            session.endStream()
            break

        # Check for timeout
        if readout is None:
            print('readout is none')
            continue
        if options.bsub:
            applyPatternSubtraction(readout)
        wf = readout["waveform"]
        sumwf += np.array(wf)
        # Fix for 0x6a firmware
        if len(wf) != int(nSamples):
            print(f'#sample is wrong : {len(wf)}, {nSamples}')
            time.sleep(0.1)
            continue
        if not line:
            line, = ax.plot(xdata, wf, 'r-')
        else:
            line.set_ydata(wf)
        if (options.adcMin is None or options.adcRange is None):
            wfrange = (max(wf) - min(wf))
            plt.axis([0, len(wf),
                      max(wf) - wfrange * 1.2, min(wf) + wfrange * 1.2])
        else:
            plt.axis([0, len(wf), int(options.adcMin),
                      int(options.adcMin) + int(options.adcRange)])
        fig.canvas.draw()
        fig.canvas.flush_events()
        #plt.savefig(f'save/fig{index}.png',format='png',dpi=300)
        plt.pause(0.001)
        print(f'\r{index}',end='')

    session.setDEggHV(int(options.channel), 0)
    session.disableHV(int(options.channel))

if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser)

