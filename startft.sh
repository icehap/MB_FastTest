#!/bin/bash 

input=$(zenity --forms --title="Start Fast-Test" \
  --text="Enter in English..." \
  --separator="," \
  --add-entry="snum" \
  --add-entry="host" \
  --add-entry="port" \
  --add-entry="author") 

echo $input 

#source setup.sh 

python3 execute.py "$input"

zenity --info --title="Fast-Test" --text="Done!"
