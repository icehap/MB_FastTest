# MB_FastTest
Codes for the IceCube-Upgrade D-Egg mainboard Fast-Testing. (supports Rev 3<)

- The main script: mbfasttest.py includes all testing items. If runing the code, the script takes the data from the mainboard, automatically analyzes the data, and then generates a PDF-format report. 
Available to use the same options as the iceboot. 
- Waveform taking: thresSpeCurve.py 
- Charge stamp taking: Qhist_chargestamp.py

The package WIPACrepo/STM32Tools is required (need access permission). It is not automatically downloaded with the "git clone". Do it manally and put it in the correct path shown below. 

### Add the module path to PYTHONPATH: 
```
$ export PYTHONPATH=$PYTHONPATH:[working dir]/MB_FastTest/testitems:[working dir]/tools/python
```
This is automatically set by running setup.sh. 

### Run the main fast-test script: 
```
$ python3 mbfasttest.py --host=[host IP] --port=[port] --mbsnum=[S/N] --author=[author]
```

### Options: 
- `--host=[IP address]`
- `--port=[port number]`
- `--mbsnum=[serial number]`
   - The serial number can be set manually, not depends on the hardware ID, software ID, and so on.
- `--author=[author name]`
- `--dacscanmode=[mode]`
   - This sets the precision of the DAC scan. From 0 to 8 is available. The #points increases if set larger number. Default is 5, corresponding to 10 scan points. 
- `--samples=[number of sampling bins in a waveform]` 
   - Default: 256 (same as the standard iceboot procedure)
- `--nevents=[number of events for each point of the DAC scan]` 
   - Default: 10
