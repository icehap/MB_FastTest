#!/bin/env python3 

from iceboot.iceboot_session import getParser
import codecs 
import os 

import fwswversion
import dacscan
import scope
import sensorcheck
from addparser_iceboot import AddParser

def main():
    print ("test")
    parser = getParser()
    scope.AddParser(parser)

    (options, args) = parser.parse_args()
    print (options.channel)

    MBserialnumber = options.mbsnum

    makereport(parser,MBserialnumber)

    os.system("rm *.aux *.log")

def makereport(parser,snum): 
    ofilename = 'test_' + snum + '.tex'

    inforeport = getConfInfo(parser)

    finalacc = 1
    sensorreport, sensorbool = rep_sensor(parser)
    finalacc *= sensorbool
    dacscanreport, dacscanbool = rep_dacscan(parser)
    finalacc *= dacscanbool

    f = codecs.open(ofilename,'w', 'utf-8')
    f.write(preamble(parser,snum))
    f.write(beginconts(finalacc))
    
    ### add contents below
    f.write(inforeport)
    f.write(sensorreport)
    f.write(dacscanreport)
    ### above
    
    f.write(endconts())
    f.close()

    os.system('pdflatex ' + ofilename)
    os.system('pdflatex ' + ofilename)


PASS = r'''{\begin{center} \checkbox{black!30!green} PASS \hspace{2ex} \checkbox{white} FAIL \end{center}}'''
FAIL = r'''{\begin{center} \checkbox{white} PASS \hspace{2ex} \checkbox{red} FAIL \end{center}}'''

def rep_sensor(parser):
    thresMin, thresMax, out, outbool = sensorcheck.main(parser) 
    
    SECTIONNAME = r'''\section{Slow Monitoring and Sensors}'''

    citems = ['+1V1 Current','+1V35 Current', '+1V8 Current', '+2V5 Current', '+3V3 Current', '+1V8\_A Voltage', 'Light Sensor', 'Temperature', 'HV ch0 Voltage', 'HV ch0 Current', 'HV ch1 Voltage', 'HV ch1 Current', '+1V1 Voltage', '+1V35 Voltage', '+2V5 Voltage', '+3V3 Voltage', 'Pressure']
    units = ['~mA', '~mA', '~mA', '~mA', '~mA', '~V', '~mV', '${}^{\circ}$C', '~V', '~$\mu$A', '~V', '~$\mu$A', '~V', '~V', '~V', '~V', '~hPa']
    criteriapres = 'Pressure    & $' + str(thresMin[16]) + '\leq x \leq ' + str(thresMax[16]) + '$ & ' + str(out[16]) + ' & \judgemark{' + str(outbool[16]) + '} '  

    CONTENTSBEGIN = r'''
\begin{table}[h]
\centering
\caption{Slow Monitoring ADC \& Sensors Test Summary.}
\begin{tabular}{lrclrc}
\toprule 
Sensor & \multicolumn{3}{c}{Criterion}  & Observed & Acceptance \\
\midrule ''' 

    omittest = [0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0]
    #omittest = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

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


def rep_dacscan(parser):
    path = 'testitems/'
    results, minvalues = dacscan.dacscan(parser,path)
    (options, args) = parser.parse_args()

    SECTIONNAME = r'''\section{DAC Scan Result}'''
    
    FIGURE = r'''
\begin{figure}[h]
\centering
\includegraphics[width=.8\textwidth]{''' + path + '/' + str(options.mbsnum) + '''/DACscanPlot.pdf}
\caption{DAC scan plot.}
\end{figure}
    '''

    FIGURE2 = r'''
\begin{figure}[h]
\centering
\includegraphics[width=.8\textwidth]{''' + path + '/' + str(options.mbsnum) + r'''/DACscanFFT0Plot.pdf}
\subcaption{Channel 0}
\includegraphics[width=.8\textwidth]{''' + path + '/' + str(options.mbsnum) + r'''/DACscanFFT1Plot.pdf}
\subcaption{Channel 1}
\caption{FFT plots at the DAC value where the noise RMS is minimum. }
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
ADC Ch\# & Criterion & \multicolumn{1}{c}{Min(Obs)} & Acceptance \\ 
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
    fwVer, swVer, flashLS, swid = fwswversion.main(parser)

    CONTENTS = r'''
\section{Test Configuration} 
Successfully installed the firmware from the flash memory on the mainboard. 
\begin{table}[h]
\centering
\caption{Test Configuration Summary.}
\begin{tabular}{ccl}
\toprule 
Contents & Values & \multicolumn{1}{c}{Comments} \\ \midrule '''
    Names  = ['Host IP Address', 'Port Number', 'FPGA FW Version', 'Iceboot SW Version']
    Values = [str(options.host), str(options.port), f'0x{fwVer:x}', f'{swVer:x}']
    Comments = ['','', r'''filename: \verb|'''+ flashLS[0]['Name'] +'|', 'softwareID: ' + str(swid) ]

    for i in range(len(Names)):
        CONTENTS += Names[i] + ' & ' + Values[i] + ' & ' + Comments[i] + r'''\\'''

    CONTENTS += r'''
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
\usepackage[subrefformat=parens]{subcaption}
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
