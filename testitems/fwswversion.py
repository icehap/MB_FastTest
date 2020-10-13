#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
from addparser_iceboot import AddParser
import sys
import time

def main(parser):
    session = startIcebootSession(parser)
    flashLS = session.flashLS()

    if len(flashLS) == 0: 
        print('Valid firmware images not found. \n' + 
                'Please upload the correct image file into the flash memory before running the script. ')
        sys.exit(0)

    firmwarefilename = flashLS[len(flashLS)-1]['Name'] # latest uploaded file
    print(f'Found valid firmware {firmwarefilename} in the flash memory.\n' + 
            'Try to configure... ')
    
    try : 
        session.flashConfigureCycloneFPGA(firmwarefilename)
    except : 
        print(f'Error during the loading firmware {firmwarefilename}. Exit.')
        session.close()
        sys.exit(0)
    else :
        time.sleep(0.1)

    FpgaVersion = session.fpgaVersion()
    SoftwareVersion = session.softwareVersion()
    SoftwareId = session.softwareId()
    FpgaId = session.fpgaChipID()
    FlashId = session.flashID()

    print (f'FPGA: {FpgaId} with Firmware ver.{hex(FpgaVersion)}, Flash ID: {FlashId}, ' +  
            f'Software ver.{hex(SoftwareVersion)} with ID {SoftwareId}. ')

    session.close()
    return FpgaVersion, SoftwareVersion, flashLS, SoftwareId, FpgaId, FlashId

if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser)
