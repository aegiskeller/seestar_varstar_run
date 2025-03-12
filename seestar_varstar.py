# create a function to run the seestar_run.py script for a given star

import os
import subprocess
import numpy as np
import pandas as pd
import seestar_params as sp

def seestar_run(targetName, coords, exptime):
    # Define the path to the seestar_run.py script
    #using subprocess to add arguments
    subprocess.run(['python', f'{}/seestar_run.py', sp.seestar_ip, targetName, str(coords[0]), str(coords[1]), '0', str(exptime), '1', '1', '1', '1'])

    seestar_run_path = f'{sp.path}/seestar_run.py {sp.seestar_ip} \'{targetName}\' {coords[0]} {coords[1]} 0 {exptime} 1 1 1 1'
    
    # Run the seestar_run.py script and check for errors
    try:
        subprocess.run(['python', seestar_run_path])
    except:
        print('Error running seestar_run.py')
        return 1
    return 0

#example
seestar_run('kobli Kai', [5, -10], 10)