#!/bin/bash

echo 'export PYTHONPATH for the package. Please add STM32Tools/python manually if failed.'

export PYTHONPATH=$PYTHONPATH:$PWD/testitems:$PWD/tools/python
