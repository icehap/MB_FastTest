import matplotlib.pyplot as plt
import numpy as np
import tables
import sys
import os
import glob
from natsort import natsorted

def mkplot(path):
    plt.ion()
    plt.show()
    fig = plt.figure()
    plt.xlabel("Mean [LSB]", ha='right', x=1.0)
    plt.ylabel("Noise RMS [LSB]", ha='right', y=1.0)
    line = None

    #filenames = [f.name for f in os.scandir(path) if f.is_file()]
    filenames = []

    pathdata = path + '/*.hdf5'
    filenames = glob.glob(pathdata)

    #print (filenames) 

    x, y, yerr = mkDataSet(natsorted(filenames))

    #print(f'{x} {y} {yerr}')

    plt.errorbar(x,y,yerr=yerr,capsize=2,fmt='o',ms=5,ecolor='black',markeredgecolor='black',color='w')
    plt.plot(x,y)

    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.001)
    plt.savefig(path+'/DACscanPlot.pdf')

    if min(y) < 2.5: 
        return 1
    else:
        return 0

def mkDataSet(filenames):
    x = []
    y = []
    yerr = []

    for i in range(len(filenames)):
        x_1, y_1, yerr_1 = getData(filenames[i])

        x.append(x_1)
        y.append(y_1)
        yerr.append(yerr_1)

    return x, y, yerr
    

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

    x = np.mean(meanwf)
    y = np.mean(rms)
    yerr = getArrRMS(np.array(rms))

    f.close()

    return x, y, yerr

def getArrRMS(array):
    reducedArray = array - np.mean(array)
    rms  = np.sqrt(np.mean(np.square(reducedArray))-np.mean(reducedArray)**2)
    
    return rms

if __name__ == "__main__":
    mkplot(sys.argv[1])
