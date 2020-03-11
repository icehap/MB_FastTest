#!/bin/env python3 

from iceboot.iceboot_session import getParser
import codecs 
import os 

import dacscan
import scope

def main():
    print ("test")
    parser = getParser()
    scope.AddParser(parser)

    (options, args) = parser.parse_args()
    print (options.channel)

    MBserialnumber = options.mbsnum

    #return 

    makereport(parser,MBserialnumber)

    os.system("rm *.aux *.log")

def makereport(parser,snum): 
    ofilename = 'test_' + snum + '.tex'

    finalacc = 1
    dacscanreport, dacscanbool = rep_dacscan(parser)
    finalacc *= dacscanbool

    f = codecs.open(ofilename,'w', 'utf-8')
    f.write(preamble(snum))
    f.write(beginconts(finalacc))
    ### add contents below
    f.write(dacscanreport);
    ### above
    f.write(endconts())
    f.close()

    os.system('pdflatex ' + ofilename)
    os.system('pdflatex ' + ofilename)

PASS = r'''{\begin{center} \checkbox{black} PASS \hspace{2ex} \checkbox{white} FAIL \end{center}}'''
FAIL = r'''{\begin{center} \checkbox{white} PASS \hspace{2ex} \checkbox{black} FAIL \end{center}}'''

def rep_dacscan(parser):
    path = 'testitems/'
    result = dacscan.dacscan(parser,path)
    (options, args) = parser.parse_args()

    SECTIONNAME = r'''\section{DAC Scan Result}'''
    
    CONTENTS = r'''
\begin{figure}[h]
\centering
\includegraphics[width=.8\textwidth]{''' + path + '/' + str(options.mbsnum) + '''/DACscanPlot.pdf}
\caption{DAC scan plot.}
\end{figure}
    '''

    if result==1: 
        CONTENTS = SECTIONNAME + PASS + CONTENTS
    else:
        CONTENTS = SECTIONNAME + FAIL + CONTENTS

    return CONTENTS, result

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


def preamble(snum):
    
    PREAMBLE = r'''
\documentclass[a4paper,11pt]{article}
\usepackage[vmargin={2.8cm,3cm}, hmargin=2.8cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{palatino}
\usepackage{mathpazo}
\usepackage{graphicx}
\usepackage{color}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{ascmac}
\usepackage{fancybox}
\fancypagestyle{mypagestyle}{
\renewcommand{\headrulewidth}{0pt}
\lhead{\textit{MB} \#\underline{\ '''+ snum + r'''\ }}
\rhead{\textit{Date:}\underline{\ \today\ }}
\cfoot{\thepage\ / \pageref{LastPage}}
}

\pagestyle{mypagestyle}
\newcommand{\checkbox}[1]{\hspace{2ex}\fbox{\textcolor{#1}{\LARGE{\checkmark}}}}
    '''

    TITLE = r'''
\title{\sffamily D-Egg Mainboard Fast-Testing Report \\[1ex] for \# 
\underline{\ ''' + snum + r'''\ }}'''

    authorname = 'R.~Nagai'

    AUTHOR = r'''
    \author{Tested by: '''+ authorname + '}'

    return PREAMBLE + TITLE + AUTHOR

if __name__ == "__main__":
    main()
