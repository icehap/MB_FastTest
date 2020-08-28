#!/bin/env python3 

from iceboot.iceboot_session import getParser
import codecs 
import os 
import sys
import platform
import datetime
import time

import fwswversion
import dacscan
import scope
import sensorcheck
import pulserCalib
import hvcheck
from addparser_iceboot import AddParser

def main():
    parser = getParser()
    scope.AddParser(parser)

    (options, args) = parser.parse_args()
    print (options.channel)

    snum = options.mbsnum
    if len(snum.split('/')) > 1: 
        print('Do not use "/" in the MB serial number. Exit.')
        sys.exit(0)

    date = datetime.date.today()
    index = 1
    prepath = f'results/FastTest/{snum}/{date}/Run'
    path = f'{prepath}{index}'

    while os.path.isdir(path): 
        index = index + 1 
        path = f'{prepath}{index}'
    
    print(f'=== File path is: {path}. ===')
    os.system(f'mkdir -p {path}')

    makereport(parser,snum,path)

    os.system(f'rm {path}/*.aux {path}/*.log')

def makereport(parser,snum,path='.'): 
    (options, args) = parser.parse_args()
    ofilename = f'test_{snum}.tex'
    ofpath = f'{path}/{ofilename}'

    inforeport = getConfInfo(parser)

    finalacc = 1
    sensorreport, sensorbool = rep_sensor(parser)
    finalacc *= sensorbool
    dacscanreport, dacscanbool = rep_dacscan(parser,path)
    finalacc *= dacscanbool
    pulserreport = rep_pulser(parser,path)

    f = codecs.open(ofpath,'w', 'utf-8')
    f.write(preamble(parser,snum))
    f.write(beginconts(finalacc))
    
    ### add contents below
    f.write(inforeport)
    f.write(sensorreport)
    f.write(dacscanreport)
    f.write(pulserreport)
    if int(options.hven)!=-1: 
        f.write(put_figures(snum,hvcheck.main(parser,path),path))
    ### above
    
    f.write(endconts())
    f.close()

    os.system(f'pdflatex -output-directory {path} {ofilename}')
    os.system(f'pdflatex -output-directory {path} {ofilename}')


PASS = r'''{\begin{center} \checkbox{black!30!green} PASS \hspace{2ex} \checkbox{white} FAIL \end{center}}'''
FAIL = r'''{\begin{center} \checkbox{white} PASS \hspace{2ex} \checkbox{red} FAIL \end{center}}'''


def rep_sensor(parser):
    (options, args) = parser.parse_args()
    thresMin, thresMax, out, outbool, citems, units = sensorcheck.main(parser) 
    
    SECTIONNAME = r'''\section{Slow Monitoring and Sensors}'''

    CONTENTSBEGIN = r'''
\begin{table}[h]
\centering
\caption{Slow Monitoring ADC \& Sensors Test Summary.}
\begin{tabular}{lrclrc}
\toprule 
SLO ADC or Sensor & \multicolumn{3}{c}{Criteria}  & \multicolumn{1}{c}{Observed} & Acceptance \\
\midrule ''' 

    omittest = [0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0]
    if int(options.hven) == 0: # HV0 enabled, HV1 disabled
        omittest[8] = 0
        omittest[9] = 0
    elif int(options.hven) == 1: # HV0 disabled, HV1 enabled
        omittest[10] = 0
        omittest[11] = 0
    elif int(options.hven) == 2: # HV0 enabled, HV1 enabled
        omittest[8] = 0
        omittest[9] = 0
        omittest[10] = 0
        omittest[11] = 0

    result = 1
    for i in range(len(out)):
        criterion = citems[i] + ' & ' + str(thresMin[i] ) + r'''& \llap{$\leq$} $x$ \rlap{$\leq$}& ''' + str(thresMax[i] ) + ' & ' + str(out[i] ) + units[i] + ' & \judgemark{' + str(outbool[i] ) + '} '  
        CONTENTSBEGIN += criterion + r'''\\'''
        if omittest[i]==0: 
            result *= outbool[i]
    
    CONTENTSEND = r'''
\bottomrule
\end{tabular}
\end{table}
    '''

    CONTENTS = CONTENTSBEGIN + CONTENTSEND

    if result==1:
        CONTENTS = SECTIONNAME + PASS + CONTENTS
    else:
        CONTENTS = SECTIONNAME + FAIL + CONTENTS

    return CONTENTS, result

def rep_pulser(parser,path='testitems'):
    results, minvalues = pulserCalib.pulserCalib(parser,path)
    (options, args) = parser.parse_args()

    SECTIONNAME = r'''\section{AFE Pulser Calibration}'''

    FIGURE = r'''
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw' + '''/PlsrCalibPlot.pdf}
\caption{AFE pulser calibration plot.}
\end{figure}
    '''
    FIGURE = FIGURE + r'''
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw' + '''/PlsrCalib_WF.pdf}
\caption{Waveform example with the FE pulse.}
\end{figure}
    '''

    CONTENTS = SECTIONNAME + FIGURE

    return CONTENTS

def put_figures(snum,figurenames,path='testitems'):
    if len(figurenames) < 4: 
        return ""
    FIGURE = r'''
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw/{figurenames[0]}' + r'''}
\caption{''' + str(figurenames[1]) + r'''}
\end{figure}
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw/{figurenames[2]}' + r'''}
\caption{''' + str(figurenames[3]) + '''}
\end{figure}
'''
    return FIGURE
    

def rep_dacscan(parser,path='testitems'):
    results, minvalues = dacscan.dacscan(parser,path)
    (options, args) = parser.parse_args()

    SECTIONNAME = r'''\section{DAC Scan Result}'''
    
    FIGURE = r'''
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw'  + '''/DACscanPlot.pdf}
\caption{DAC scan plot.}
\end{figure}
    '''

    FIGURE2 = r'''
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw' + r'''/DACscanFFT0Plot.pdf}
\caption{Channel 0 FFT plot at the DAC value where the noise RMS is minimum. }
\end{figure}
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw' + r'''/DACscanFFT1Plot.pdf}
\caption{Channel 1 FFT plot at the DAC value where the noise RMS is minimum. }
\end{figure}
    '''

    FIGURE2 =  FIGURE2 + r'''
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw' + r'''/DACscanMFFT0Plot.pdf}
\caption{Channel 0 FFT plot at the DAC value where the noise RMS is maximum. }
\end{figure}
\begin{figure}[h]
\centering
\includegraphics[width=.9\textwidth]{''' + f'{path}/raw' + r'''/DACscanMFFT1Plot.pdf}
\caption{Channel 1 FFT plot at the DAC value where the noise RMS is maximum. }
\end{figure}
    '''

    CONTENTS = ''

    if len(results) != 2: 
        CONTENTS = SECTIONNAME + FAIL + 'COULDN\'T GET DATA...'
    else:
        result = results[0] * results[1]
        TABLEBEGIN = r'''
\begin{table}[h]
\centering
\caption{DAC Scan Summary.}
\begin{tabular}{ccrc}
\toprule
ADC Ch\# & Criteria & \multicolumn{1}{c}{Min(Obs)} & Acceptance \\ 
\midrule '''
        TABLEEND = r'''
\bottomrule
\end{tabular}
\end{table} '''
        for i in range(2): 
            TABLEBEGIN += str(i) + '& Min(Obs) $<$ 2.5 &' + f'{minvalues[i]:.2f}' + '~[LSB] & \judgemark{' + str(results[i]) + r'''} \\'''

        if result==1: 
            CONTENTS = SECTIONNAME + PASS + TABLEBEGIN + TABLEEND + FIGURE + FIGURE2
        else: 
            CONTENTS = SECTIONNAME + FAIL + TABLEBEGIN + TABLEEND + FIGURE + FIGURE2

    return CONTENTS, result

def getConfInfo(parser):
    (options, args) = parser.parse_args()
    fwVer, swVer, flashLS, swid, fpgaId, flashId = fwswversion.main(parser)

    CONTENTS = r'''
\section{Test Configuration} 
Successfully installed the firmware from the flash memory on the mainboard. 
\begin{table}[h]
\centering
\caption{Test Configuration Summary.}
\begin{tabular}{ll}
\toprule 
Contents & Values \\ \midrule '''
    
    flashLSoutput = str(flashLS[len(flashLS)-1]['Name']).split('_')
    fnameinflash = ''
    for i in range(len(flashLSoutput)):
        fnameinflash += flashLSoutput[i]
        if i+1 < len(flashLSoutput):
            fnameinflash += '\_'

    ipcomments = ''
    if str(options.host) != 'localhost':
        ipcomments = 'Using Ethernet connection'
    else:
        ipcomments = 'Using Mini-FieldHub'

    Names  = ['Flash ID','FPGA Chip ID','Host IP Address', 'Port Number','FPGA FW Ver.', 'Iceboot SW Ver.']
    Values = [str(flashId), str(fpgaId), f'{options.host}; {ipcomments}', str(options.port), f'0x{fwVer:x}; File: {fnameinflash}', f'{swVer:x}; ID: {swid}']

    for i in range(len(Names)):
        CONTENTS += f'{Names[i]} & {Values[i]}' + r' \\'
        if i==1: 
            CONTENTS += r'''\midrule '''

    hvcomments = ['HV0: Not connected, HV1: Not connected.','HV0: Connected, HV1: Not connected.', 'HV0: Not connected, HV1: Connected.', 'HV0: Connected, HV1: Connected.']
    CONTENTS += r'''
\midrule 
HV Boards & ''' + hvcomments[int(options.hven)+1] + r''' \\ 
Camera & Not connected.  \\ 
\midrule
OS & '''
    
    platformoutput = platform.platform().split('_')
    for i in range(len(platformoutput)):
        CONTENTS += platformoutput[i]
        if i+1 < len(platformoutput):
            CONTENTS += r'\_'

    CONTENTS += r'''\\
Python Ver. & ''' + sys.version + r'''  \\
Test Date & ''' + (datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S") + r''' \\
\bottomrule
\end{tabular}
\end{table}'''

    return CONTENTS

def beginconts(result):
    CONTENTS = r'''
\begin{document}
\maketitle
\thispagestyle{mypagestyle}
\begin{screen}\centering\Large \underline{FINAL ACCEPTANCE}
    '''
    if result==1: 
        CONTENTS = CONTENTS + PASS + '\end{screen}'
    else:
        CONTENTS = CONTENTS + FAIL + '\end{screen}'

    return CONTENTS

def endconts():
    CONTENTS = r'''
\end{document}
    '''
    return CONTENTS


def preamble(parser,snum):
    (options, args) = parser.parse_args()
    
    PREAMBLE = r'''
\documentclass[a4paper,11pt]{article}
\usepackage[vmargin={2.8cm,3cm}, hmargin=2.8cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{palatino}
\usepackage{mathpazo}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{ascmac}
\usepackage{fancybox}
\usepackage{booktabs}
\usepackage{ifthen}
\fancypagestyle{mypagestyle}{
\renewcommand{\headrulewidth}{0pt}
\lhead{\textit{MB} \#\underline{\ '''+ snum + r'''\ }}
\rhead{\textit{Date:}\underline{\ \today\ }}
\cfoot{\thepage\ / \pageref{LastPage}}
}
\pagestyle{mypagestyle}

\newcommand{\checkbox}[1]{\hspace{2ex}\fbox{\textcolor{#1}{\LARGE{\checkmark}}}}
\newcommand{\judgemark}[1]{\ifthenelse{\equal{#1}{1}}{\textcolor{black!30!green}{\textbf{PASS}}}{\textcolor{red}{\textbf{FAIL}}}}
\usepackage{afterpage,array,rotating}
\newcolumntype{Y}{>{\centering\arraybackslash}p{1ex}}
    '''

    TITLE = r'''
\title{\sffamily D-Egg Mainboard Fast-Test Report \\[1ex] for \# 
\underline{\ ''' + snum + r'''\ }}'''

    authorname = str(options.author)

    AUTHOR = r'''
    \author{Tested by: '''+ authorname + '}'

    return PREAMBLE + TITLE + AUTHOR

if __name__ == "__main__":
    main()
