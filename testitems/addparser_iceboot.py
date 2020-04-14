from iceboot.iceboot_session import getParser

def AddParser(parser):
    parser.add_option("--mbsnum",dest="mbsnum",
                      help="MB serial number (just for testing)",default="Not-Available")
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
