#!/bin/env python3 

import os, sys

def main():
    arglist = sys.argv[1].split(",")
    if len(arglist) < 4: 
        print("ERROR: Need at least 4 parameters.") 
        print("Exit.")
        sys.exit(1)

    os.system(f'python3 mbfasttest.py --mbsnum="{arglist[0]}" --host="{arglist[1]}" --port="{arglist[2]}" --author="{arglist[3]}"')
    sys.exit(0)

if __name__ == "__main__":
    main()




