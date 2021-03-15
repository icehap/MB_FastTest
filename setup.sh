#!/bin/bash

echo 'export PYTHONPATH for the package.' 
echo 'STM32Tools/python path is automatically added as ../Tools/python.'

export PYTHONPATH=$PYTHONPATH:$PWD/testitems:$PWD/../Tools/python
export FTHOME=$PWD
