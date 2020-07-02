#!/bin/bash 

input=$(zenity --forms --title="Start Fast-Test" \
  --text="Enter in English..." \
  --separator="," \
  --add-entry="snum" \
  --add-entry="host" \
  --add-entry="port" \
  --add-entry="author")

hvcheck=$(zenity --list --checklist \
  --title="HV selection" \
  --column="Check" \
  --column="HVB setting" \
  False "HVB channel 0" False "HVB channel 1" --separator=",")

echo $input 
echo $hvcheck

source setup.sh 

python3 execute.py "$input" "$hvcheck"

zenity --width=200 --info --title="Fast-Test" --text="Done!\nPlease check the result. If you observed any problems, run it again."
