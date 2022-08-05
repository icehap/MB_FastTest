import datetime 
import os

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

    return path

