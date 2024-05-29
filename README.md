# MB_FastTest
Code set for the IceCube-Upgrade D-Egg mainboard simple testing (supports mainboard Rev 3<). Here are listed (currently) available scripts, giving simple descriptions, while the detailed docs can be provided in the following sub-sections. *Recommends comfirmation of the ICM firmware set to the runtime image (usually loading from the slot 2) before running every scripts*. 

- `mbfasttest.py`: the main script. It includes all testing items. If runing the script, it takes the data from the mainboard, automatically analyzes them, and then generates a PDF-format report. 
Available to use the same options as the iceboot (see STM32Tools). 
- `thresSpeCurve.py`: waveform-based data-taking script. It accepts several trigger settings.  
- `Qhist_chargestamp.py`: charge-stamp-based data-taking script. It accepts several trigger settings.

The package includes directories:
- `analysis/`: scripts for analyses. They can be used in some executing scripts or be worked standalone.
- `scripts/`: contains special runs especially for the pre-FAT.
- `testitems/`: includes testing programs used in the executing scripts. 
- `utils/`: stores initial settings, common options, and so on. The codes are migrated from codes in `testitems`, but not yet completed. 

## Setup
The packages `WIPACrepo/STM32Tools` as well as `WIPACrepo/fh_icm_api` are required (you need the access permission to get both). They are not automatically downloaded by `git clone`. Do it manally. The ideal directory structure is shown below:
```
$ ls
MB_FastTest/ Tools/ fh_icm_api/
```
Note that the `STM32Tools` is renamed to `Tools` in this instruction. 

### Add the module path to PYTHONPATH: 
```
$ export PYTHONPATH=$PYTHONPATH:$PWD/MB_FastTest/testitems:$PWD/Tools/python:$PWD/fh_icm_api
```
Or, you just run setup.sh: 
```
$ cd MB_FastTest
$ source setup.sh
```

## Running scripts

### Run the main fast-test script 
```
$ python3 mbfasttest.py --host=[host IP] --port=[port] --mbsnum=[S/N] --author=[author]
```
#### Options: 
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
 
### Run the SPE check for the pre-FAT (so-called "SPELED")
```
$ python3 scripts/spe_by_led.py
```
#### Options:
- `--mbsnum=[serial number]`
