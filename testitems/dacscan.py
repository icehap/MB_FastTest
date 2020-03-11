#!/usr/bin/env python3

from iceboot.iceboot_session import getParser
import mkplot
import os
import sys
import numpy as np
import scope 

def dacscan(parser, path='.'):
    (options, args) = parser.parse_args()

    snum = options.mbsnum

    datapath = path + '/' + snum

    os.system('mkdir -p ' + datapath)

    nevts = '10'
    nsamples = '500'

    #dacvalue = np.linspace(12,48,37)
    dacvalue = np.linspace(12,48,10)
    dacvalue10 = dacvalue.astype('int') * 1000 

    for i in range(len(dacvalue10)):
        scope.main(parser,dacvalue10[i], path)

    result = mkplot.mkplot(datapath)

    return result


if __name__ == "__main__":
    parser = getParser()
    scope.AddParser(parser)
    dacscan(parser,'.')
