# MB_FastTest
Codes for the IceCube-Upgrade D-Egg Rev.4 mainboard Fast-Testing.

The main script: mbfasttest.py includes all testing items. If run the code, the script takes the data from the mainboard, automatically analyzes the data, and then generates a report. 
Available to use the same options as the iceboot. 

The package STM32Tools in the WIPACrepo is required. It is not automatically downloaded with the "git clone". 

### Add the module path to PYTHONPATH: 
```
$ export PYTHONPATH=$PYTHONPATH:[working dir]/MB_FastTest/testitems:[working dir]/tools/python
```

### Run the main script: 
```
$ python3 mbfasttest.py --host=[host IP] --port=[port] --mbsnum=[S/N] --author=[author]
```

### Options: 
- `--host=[IP address]`
- `--port=[port number]`
- `--mbsnum=[serial number]`
 - ** The serial number can be set manually, not depends on the hardware ID, software ID, and so on.
- `--author=[author name]`
- `--dacscanmode=[mode]`
 - ** This sets the precision of the DAC scan. From 0 to 8 is available. The #points increases if set larger number. Default is 5, corresponding to 10 scan points. 
- `--samples=[number of sampling bins in a waveform]` 
 - ** Default: 256 (same as the standard iceboot procedure)
- `--nevents=[number of events for each point of the DAC scan]` 
 - ** Default: 10
