#!/bin/bash

echo 'export PYTHONPATH for the package.' 
echo 'STM32Tools/python path is automatically added as ../Tools/python.'

export FTHOME=$PWD
export PYTHONPATH=$PYTHONPATH:$FTHOME/testitems:$FTHOME/../Tools/python:$FTHOME/../fh_icm_api
export PYTHONPATH=$PYTHONPATH:$FTHOME/analysis
