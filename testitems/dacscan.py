#!/usr/bin/env python3

from iceboot.iceboot_session import getParser
import mkplot
import os
import sys
import numpy as np
import scope 
from addparser_iceboot import AddParser

def dacscan(parser, path='.'):
    (options, args) = parser.parse_args()

    snum = options.mbsnum

    datapath = f'{path}/raw'

    os.system(f'mkdir -p {datapath}')

    #modes = [1,2,3,4,6,9,12,18,36,72] # divisors of 36 (=48-12)
    modes = [1,2,4,8,16,32,64,128,256] # divisors of 64 
    mode = modes[1] + 1
    if int(options.dsmode) < len(modes):
        mode = modes[int(options.dsmode)] + 1

    dacvalue = np.linspace(0,64,mode)
    dacvalue10 = dacvalue * 1000 

    for i in range(len(dacvalue10)):
        scope.main(parser,0,int(dacvalue10[i]), path)
        scope.main(parser,1,int(dacvalue10[i]), path)

    result, minvalues = mkplot.mkplot(datapath,options.b)

    return result, minvalues


if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)
    dacscan(parser,'.')
