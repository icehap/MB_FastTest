#!/usr/bin/env python3

from iceboot.iceboot_session import getParser
import mkplot
import os
import sys
import numpy as np
import scope 

#def dacscan(path, snum_d, IP='10.25.120.111', Port='5012'):
def dacscan(parser, path='.'):
    #parser = getParser()
    #scope.AddParser(parser)
    (options, args) = parser.parse_args()

    snum = options.mbsnum
    #path = '.'

    datapath = path + '/' + snum

    os.system('mkdir -p ' + datapath)

    #IP = '10.25.120.111'
    #Port = '5012'
    nevts = '10'
    nsamples = '500'

    #dacvalue = np.linspace(12,48,37)
    dacvalue = np.linspace(12,48,10)
    dacvalue10 = dacvalue.astype('int') * 1000 

    #print (dacvalue10[0].astype('str'))
    
    
    for i in range(len(dacvalue10)):
        scope.main(parser,dacvalue10[i], path)
        #os.system('python3 ' + path + '/scope.py --filename="' + datapath + '/test_' + dacvalue10[i].astype(str) + '.hdf5" --host=' + IP +  ' --port=' + Port + ' --samples=' + nsamples + ' --nevents=' + nevts + ' --setDAC=A,' + dacvalue10[i].astype(str))
    

    result = mkplot.mkplot(datapath)

    return result


if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)
    dacscan(parser,'.')
