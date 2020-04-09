#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
from addparser_iceboot import AddParser
import numpy as np

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

    #targetMax = [500,500,500,500,500,1.9,5000,60,2000,100,2000,100,1.2,1.45,2.6,3.4,2000]
    #targetMin = [  0,  0,  0,  0,  0,1.7,   0,10,   0,  0,   0,  0,1.0,1.25,2.4,3.2, 500]
    targetMax = [1000,500,500,500,500,1.9,5000,35,10,10,10,10,1.2,1.45,2.6,3.4,1200]
    targetMin = [  10, 10, 10, 10, 10,1.7,   0, 5, 0, 0, 0, 0,1.0,1.25,2.4,3.2, 900]

    outputs = []
    outbool = []
    for ch in range(17):
        output = 0
        if ch==16:
            output = session.readPressure()
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

    return targetMin, targetMax, outputs, outbool
    
def readSloAdcChannel(session, channel):
    out = session.cmd("%d sloAdcReadChannel" % (channel)) 
    outlist = out.split()

    return float(outlist[3])


if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser)
    

