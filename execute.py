#!/bin/env python3 

import os, sys

def main():
    print(len(sys.argv))
    arglist = sys.argv[1].split(",")
    if len(arglist) < 4: 
        print("ERROR: Need at least 4 parameters.") 
        print("Exit.")
        sys.exit(1)

    hven=-1
    if sys.argv[2]=="": 
        print("There is no connected HVB.")
    elif len(sys.argv[2].split(","))>1:
        print("Both channels 0 & 1 HVBs are connected.")
        hven=2
    elif len(sys.argv[2].split("0"))>1: 
        print("Channel 0 HVB is connected.")
        hven=0
    elif len(sys.argv[2].split("1"))>1:
        print("Channel 1 HVB is connected.")
        hven=1

    os.system(f'python3 mbfasttest.py --mbsnum="{arglist[0]}" --host="{arglist[1]}" --port="{arglist[2]}" --author="{arglist[3]}" --hven={hven} --hvv=200')
    sys.exit(0)

if __name__ == "__main__":
    main()




