from iceboot.iceboot_session import getParser

def AddParser(parser):
    parser.add_option("--mbsnum",dest="mbsnum",
                      help="MB serial number (just for testing)",default="Unknown")
    parser.add_option("--channel", dest="channel",
                      help="Waveform ADC channel", default="0")
    parser.add_option("--samples", dest="samples", help="Number of samples "
                               "per waveform",  default=256)
    parser.add_option("--threshold", dest="threshold",
                      help="Apply threshold trigger instead of CPU trigger "
                           "and trigger at this level", default=None)
    parser.add_option("--adcMin", dest="adcMin",
                      help="Minimum ADC value to plot", default=None)
    parser.add_option("--adcRange", dest="adcRange",
                      help="Plot this many ADC counts above min",
                      default=None)
    parser.add_option("--swTrigDelay", dest="swTrigDelay",
                      help="ms delay between software triggers",
                      default=10)
    parser.add_option("--external", dest="external", action="store_true",
                      help="Use external trigger", default=False)
    parser.add_option("--filename", dest="filename", default=None)
    parser.add_option("--timeout", dest="timeout", default=10)
    parser.add_option("--nevents", dest="nevents", default=10)
    parser.add_option("--dacscanmode",dest="dsmode", 
                      help="Set mode for DAC scan", default=5)
    parser.add_option("--author",dest="author", default="Anonymous User")
    parser.add_option("--hven",dest="hven",
                      help="HV attached or not", default=-1)
    parser.add_option("--hvv",dest="hvv",
                      help="HV values for both channels", default=0)
    parser.add_option("--baselineSubtract", dest="bsub", action="store_true",
                      help="Subtract FPGA baseline", default=False)
    parser.add_option("--bsthres", dest="bsthres", 
                      help="Threshold above baseline", default=None) 
    parser.add_option("--sppath",help="Set specific path", default=None)
    parser.add_option("--comment",help="Comment added to the output file name",default="")
    parser.add_option("--iter",help="Iteration count", default=50)
    parser.add_option("-b",action="store_false",default=True)
    parser.add_option("--degg",action="store_true",default=False)
    parser.add_option("--hvbnums",help="HVB S/N, set like '100,101' (for ch0 and 1, respectively)",default=",")
