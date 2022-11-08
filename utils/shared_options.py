def General(parser):
    parser.add_option('--mbsnum',dest='mbsnum',help='MB Serial Number',default='Unknown')
    parser.add_option('--channel',dest='channel',type='int',help='ADC channel: 0 or 1',default=0)
    parser.add_option('-b',action='store_false',help='batch mode',default=True)
    parser.add_option('--filename',dest='filename',help='Target filename',default=None)
    parser.add_option("-g",action="store_true",default=False)
    parser.add_option("--specific",help='Specific path setting',default=None)

def LED(parser):
    parser.add_option('--led',help='LED flasher on/off',action='store_true',default=False)
    parser.add_option('--freq',type='int',help='LED flasher frequency',default=10)
    parser.add_option('--intensity',type='int',help='LED flasher intensity',default=0x6000)
    parser.add_option('--ledsel',help='LED select',default='1-12')

def Waveform(parser):
    parser.add_option('--threshold',help='Apply threshold trigger at this level',default=None)
    parser.add_option('--external',help='Apply external trigger',action='store_true',default=False)
    parser.add_option('--hvv',help='Enable HV and set the value',default=None)
    parser.add_option('--swTrigDelay',help='[ms] delay between software trigs',type='int',default=10)
    parser.add_option('--bsthres',help='Apply threshold trigger at a level above baseline',default=None)
    parser.add_option('--nevents',help='#wfs',type='int',default=10)
    parser.add_option('--timeout',help='Timeout',type='int', default=10)
    parser.add_option('--samples',help='#samples',type='int',default=256)
