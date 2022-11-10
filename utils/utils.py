import datetime 
import os
import time

def pathSetting(options, measname, mon=False): 
    snum = options.mbsnum 
    if len(snum.split('/')) > 1: 
        print('Do not use "/" in the MB serial number. Exit.')
        sys.exit(0)
    
    date = datetime.date.today()
    prename = f'mon_results/{measname}/{snum}/{date}' if mon else f'results/{measname}/{snum}/{date}'
    index = 1
    if options.specific is not None:
        prepath = f'{prename}/{options.specific}/Run'
    else:
        prepath = f'{prename}/Run'
    path = prepath + str(index)

    while os.path.isdir(path):
        index = index + 1
        path = prepath + str(index)
    print(f'=== File path is: {path} ===')
    os.system(f'mkdir -p {path}')
    with open(f'{path}/log.txt','a') as f:
        f.write(f'Run date: {datetime.datetime.now()}')
        f.write(f'{options}')

    return path

def flashFPGA(session,prefer=None):
    time.sleep(0.5)
    flashLS = session.flashLS()
    fwnames = [flashLS[i]['Name'] for i in range(len(flashLS))]
    loadingFirmware = fwnames[-1]
    
    if prefer is not None:
        print(f'Preferred FPGA firmware is: {prefer}')
        for i,name in enumerate(fwnames):
            if name.split('.')[0] == prefer.split('.')[0]:
                loadingFirmware = name
                break

    print(f'loading FPGA firmware: {loadingFirmware} ...')
    try:
        session.flashConfigureCycloneFPGA(loadingFirmware)
    except:
        print('Error during the loading firmware. Check the status.')
        return 1
    else:
        print('Successfully configured the FPGA firmware.')
        time.sleep(1)
        return 0

def plot_setting(parser):
    (options, args) = parser.parse_args()
    if options.g:
        print('engine agg')
        import matplotlib as mpl
        mpl.use('Agg')
    elif not options.b:
        print('engine pdf')
        import matplotlib as mpl
        mpl.use('PDF')
