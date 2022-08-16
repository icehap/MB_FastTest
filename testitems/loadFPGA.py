from iceboot.iceboot_session import startIcebootSession
import time
import sensorcheck as sc

def loadFPGA(parser):
    time.sleep(0.5)
    session = startIcebootSession(parser)
    print ('loading FPGA firmware...') 
    flashLS = session.flashLS()
    firmwarefilename = flashLS[len(flashLS)-1]['Name'] # latest uploaded file
    try : 
        session.flashConfigureCycloneFPGA(firmwarefilename)
    except : 
        print(f'Error during the loading firmware {firmwarename}. Exit.')
        session.close()
        sys.exit(0)
    else : 
        print(f'Configuration of the FPGA firmware {firmwarefilename} was successfully completed. ')

    print (f'power: {sc.get_mb_power(session)} [W]')
    session.close()
    time.sleep(1.0)

