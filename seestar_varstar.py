import os
import subprocess
import numpy as np
import pandas as pd
import seestar_params as sp

def seestar_run_runner(targetName, coords, exptime):
    # Get the path to the seestar_run.py script
    seestar_run_path = os.path.join(os.path.dirname(__file__), 'seestar_emul.py')
    # Check if the seestar_run.py script exists
    if not os.path.exists(seestar_run_path):
        print('seestar_run.py does not exist')
        return 1
    # Check if the targetName is a string
    if not isinstance(targetName, str):
        print('targetName is not a string')
        return 1
    # Check if the coords is a list
    if not isinstance(coords, list):
        print('coords is not a list')
        return 1
    # Check if the coords list has two elements
    if len(coords) != 2:
        print('coords does not have two elements')
        return 1
    # Check if the first element of the coords list is a number
    if not isinstance(coords[0], (int, float)):
        print('first element of coords is not a number')
        return 1
    # Check if the second element of the coords list is a number
    if not isinstance(coords[1], (int, float)):
        print('second element of coords is not a number')
        return 1
    # Check if the exptime is a number  
    if not isinstance(exptime, (int, float)):
        print('exptime is not a number')
        return 1
    # Run the seestar_run.py script
    p = subprocess.Popen(['python', seestar_run_path, sp.seestar_ip, targetName, str(coords[0]), str(coords[1]), str(0), str(exptime), str(1),str(1),str(1),str(1)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #check the return value of the seestar_run.py script
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        print('seestar_run.py failed')
        print(stderr)
        return 1
    