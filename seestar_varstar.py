# create a function to run the seestar_run.py script for a given star

import os
import subprocess
import numpy as np
import pandas as pd

# Function to run the seestar_run.py
def seestar_run():
    # Define the path to the seestar_run.py script
    seestar_run_path = './seestar_run.py'
    
    # Run the seestar_run.py script and check for errors
    try:
        subprocess.run(['python', seestar_run_path])
    except:
        print('Error running seestar_run.py')
        return 1
    return 0

#example
seestar_run()