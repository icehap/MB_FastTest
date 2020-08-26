#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
from addparser_iceboot import AddParser
from sensorcheck import readSloAdcChannel
from loadFPGA import loadFPGA
import numpy as np
import time
import tables 

def main(parser,path="."):
    (options, args) = parser.parse_args()
    loadFPGA(parser)
    session = startIcebootSession(parser)
    filename = f'OnboardSensors{options.comment}.hdf5'

    axels = []
    magns = []
    press = []
    temps = []
    absaxels = []
    absmagns = []
    
    for i in range(int(options.iter)): 
        axeldata = session.readAccelerometerXYZ()
        absaxel = np.sqrt(np.sum(np.square(axeldata)))
        magndata = session.readMagnetometerXYZ()
        absmagn = np.sqrt(np.sum(np.square(magndata)))
        pressure = session.readPressure()
        temperature = readSloAdcChannel(session,7)
        axels.append(axeldata)
        magns.append(magndata)
        press.append(pressure)
        temps.append(temperature)
        absaxels.append(absaxel)
        absmagns.append(absmagn)
        with tables.open_file(filename,'a') as open_file: 
            try: 
                table = open_file.get_node('/sensor') 
            except: 
                class Sensor(tables.IsDescription):
                    time = tables.Int32Col()
                    AxelX = tables.Float32Col()
                    AxelY = tables.Float32Col()
                    AxelZ = tables.Float32Col()
                    AbsAxel = tables.Float32Col()
                    MagnX = tables.Float32Col()
                    MagnY = tables.Float32Col()
                    MagnZ = tables.Float32Col()
                    AbsMagn = tables.Float32Col()
                    Press = tables.Float32Col()
                    temp = tables.Float32Col()
                table = open_file.create_table('/','sensor',Sensor)
                table = open_file.get_node('/sensor')

            sensor = table.row
            sensor['time'] = time.time()
            sensor['AxelX'] = axeldata[0]
            sensor['AxelY'] = axeldata[1]
            sensor['AxelZ'] = axeldata[2]
            sensor['AbsAxel'] = absaxel 
            sensor['MagnX'] = magndata[0]
            sensor['MagnY'] = magndata[1]
            sensor['MagnZ'] = magndata[2]
            sensor['AbsMagn'] = absmagn
            sensor['Press'] = pressure
            sensor['temp'] = temperature
            sensor.append()
            table.flush()
    
    meanaxel = np.append(np.mean(axels,axis=0), np.mean(absaxels))
    meanmagn = np.append(np.mean(magns,axis=0), np.mean(absmagns))
    meanpres = np.mean(press)
    meantemp = np.mean(temps)
    erraxel = np.append(np.std(axels,axis=0), np.std(absaxels))
    errmagn = np.append(np.std(magns,axis=0), np.std(absmagns))
    errpres = np.std(press)
    errtemp = np.std(temps)
    with tables.open_file(filename,'a') as open_file: 
        try: 
            table = open_file.get_node('/summary')
        except: 
            class Summary(tables.IsDescription): 
                MeanAxel = tables.Float32Col(shape=np.asarray(meanaxel).shape)
                MeanMagn = tables.Float32Col(shape=np.asarray(meanmagn).shape)
                MeanPres = tables.Float32Col()
                MeanTemp = tables.Float32Col()
                ErrAxel = tables.Float32Col(shape=np.asarray(erraxel).shape)
                ErrMagn = tables.Float32Col(shape=np.asarray(errmagn).shape)
                ErrPres = tables.Float32Col()
                ErrTemp = tables.Float32Col()
            table = open_file.create_table('/','summary',Summary)
            table = open_file.get_node('/summary')

        summary = table.row
        summary['MeanAxel'] = meanaxel
        summary['MeanMagn'] = meanmagn
        summary['MeanPres'] = meanpres
        summary['MeanTemp'] = meantemp
        summary['ErrAxel'] = erraxel
        summary['ErrMagn'] = errmagn
        summary['ErrPres'] = errpres
        summary['ErrTemp'] = errtemp
        summary.append()
        table.flush()

    print(f'MeanAxel: {meanaxel}, ErrAxel: {erraxel}')
    print(f'MeanMagn: {meanmagn}, ErrMagn: {errmagn}')
    print(f'MeanPres: {meanpres}, ErrPres: {errpres}')
    print(f'MeanTemp: {meantemp}, ErrTemp: {errtemp}')
    
    return 

if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    (options, args) = parser.parse_args()
    savepath = "."
    if options.sppath:
        savepath = options.sppath
    main(parser,savepath)
    

