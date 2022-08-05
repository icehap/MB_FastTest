#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
from addparser_iceboot import AddParser
import numpy as np
import time

def main(parser):
    (options, args) = parser.parse_args()

    session = startIcebootSession(parser)
    
    '''
    Readout the slow ADC values:
    ch 0: +1V1   Current Monitor   (mA)
    ch 1: +1V35  Current Monitor   (mA)
    ch 2: +1V8   Current Monitor   (mA)
    ch 3: +2V5   Current Monitor   (mA)
    ch 4: +3V3   Current Monitor   (mA)
    ch 5: +1V8_A Voltage Monitor    (V)
    ch 6: Light Sensor output      (mV)
    ch 7: Temperature Sensor     (degC)
    ch 8: HV 0 Voltage Monitor      (V)
    ch 9: HV 0 Current Monitor    (muA)
    ch10: HV 1 Voltage Monitor      (V)
    ch11: HV 1 Current Monitor    (muA)
    ch12: +1V1  Voltage Monitor     (V)
    ch13: +1V35 Voltage Monitor     (V)
    ch14: +2V5  Voltage Monitor     (V)
    ch15: +3V3  Voltage Monitor     (V)
    '''

    citems = ['+1V1 Current','+1V35 Current', '+1V8 Current', '+2V5 Current', '+3V3 Current', '+1V8\_A Voltage', 'Light Sensor', 'Temperature', 'HV ch0 Voltage', 'HV ch0 Current', 'HV ch1 Voltage', 'HV ch1 Current', '+1V1 Voltage', '+1V35 Voltage', '+2V5 Voltage', '+3V3 Voltage', 'Pressure']
    units = ['~mA', '~mA', '~mA', '~mA', '~mA', '~V', '~mV', '${}^{\circ}$C', '~V', '~$\mu$A', '~V', '~$\mu$A', '~V', '~V', '~V', '~V', '~hPa']

    #targetMax = [500,500,500,500,500,1.9,5000,60,2000,100,2000,100,1.2,1.45,2.6,3.4,2000]
    #targetMin = [  0,  0,  0,  0,  0,1.7,   0,10,   0,  0,   0,  0,1.0,1.25,2.4,3.2, 500]
    targetMax = [1000,500,500,500,500,1.9,5000,35,int(options.hvv)+5,200,int(options.hvv)+5,200,1.2,1.45,2.6,3.4,1200]
    targetMin = [  10, 10, 10, 10, 10,1.7,   0, 5,int(options.hvv)-5,  0,int(options.hvv)-5,  0,1.0,1.25,2.4,3.2, 900]

    if options.degg: 
        targetMax[16] = 850
        targetMin[16] = 300

    outputs = []
    outbool = []

    session.enableHV(0)
    session.enableHV(1)

    session.setDEggHV(0, int(options.hvv))
    session.setDEggHV(1, int(options.hvv))

    time.sleep(5)

    for ch in range(17):
        output = 0
        if ch==16:
            try: 
                output = session.readPressure()
            except IOError: 
                output = -1
            except ValueError:
                output = -1
        else:
            output = readSloAdcChannel(session, ch)
        outputs.append(output)
        value = 0
        if isinstance(output, float):
            if targetMin[ch] <= float(output) <= targetMax[ch]:
                value = 1
            print (f'{targetMin[ch]} <= {float(output)} <= {targetMax[ch]} : {value}')
        else: 
            print (f'{targetMin[ch]} <= {output} <= {targetMax[ch]} : {value}')
        outbool.append(value)

    print (f'output value: {outbool}') 
    
    session.disableHV(0)
    session.disableHV(1)

    return targetMin, targetMax, outputs, outbool, citems, units
    
def readSloAdcChannel(session, channel):
    out = session.cmd("%d sloAdcReadChannel" % (channel)) 
    outlist = out.split()

    return float(outlist[3])

def get_mb_power(session):
    time.sleep(1)
    I1V1  = readSloAdcChannel(session, 0) 
    I1V35 = readSloAdcChannel(session, 1)
    I1V8  = readSloAdcChannel(session, 2)
    I2V5  = readSloAdcChannel(session, 3)
    I3V3  = readSloAdcChannel(session, 4)
    V1V8  = readSloAdcChannel(session, 5) 
    V1V1  = readSloAdcChannel(session, 12)
    V1V35 = readSloAdcChannel(session, 13)
    V2V5  = readSloAdcChannel(session, 14)
    V3V3  = readSloAdcChannel(session, 15)

    power = I1V1 * V1V1 + I1V35 * V1V35 + I1V8 * V1V8 + I2V5 * V2V5 + I3V3 * V3V3
    return power/1.e3 #[W]

def monitorcurrent(session, nevents, waittime=1):
    from tqdm import tqdm
    v = np.zeros((5,nevents))
    for i in tqdm(range(nevents)):
        for j in range(5):
            v[j][i] = readSloAdcChannel(session, j)
        time.sleep(waittime)
    return v

if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser)
    

