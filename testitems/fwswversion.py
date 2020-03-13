#!/usr/bin/env python3 

from iceboot.iceboot_session import getParser, startIcebootSession
from addparser_iceboot import AddParser
import sys
import time

def main(parser):
    (options, args) = parser.parse_args()

    session = startIcebootSession(parser)

    flashLS = session.flashLS()

    if len(flashLS) == 0: 
        print('Firmware images not found. \n Please upload the appropriate image file into the flash memory before running test script. ')
        sys.exit(0)

    firmwarefilename = flashLS[len(flashLS)-1]['Name'] # latest uploaded file
    
    session.flashConfigureCycloneFPGA(firmwarefilename)
    time.sleep(0.1)

    print(f'Firmware {firmwarefilename} was installed successfully.')

    FpgaVersion = session.fpgaVersion()
    SoftwareVersion = session.softwareVersion()
    SoftwareId = session.softwareId()
    FpgaId = session.fpgaChipID()
    FlashId = session.flashID()

    print (f'FPGA: {FpgaId} with FW Ver. {FpgaVersion}, Flash ID: {FlashId}, ') 
    print (f'Software Version {SoftwareVersion} with ID {SoftwareId}. ')

    return FpgaVersion, SoftwareVersion, flashLS, SoftwareId, FpgaId, FlashId

if __name__ == "__main__":
    parser = getParser()
    AddParser(parser)
    main(parser)
