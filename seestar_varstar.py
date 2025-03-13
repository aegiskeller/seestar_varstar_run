import os
import subprocess
import numpy as np
import pandas as pd
import seestar_params as sp
import logging
import argparse
from astropy.coordinates import SkyCoord
from astropy import units as u
from astroquery.simbad import Simbad
import sys

global logger

def logger():
    # Create a logger
    logger = logging.getLogger('seestar_varstar')
    logger.setLevel(logging.DEBUG)
    # Create a file handler
    fh = logging.FileHandler('seestar_varstar.log')
    fh.setLevel(logging.DEBUG)
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Add the formatter to the file handler
    fh.setFormatter(formatter)
    # Add the file handler to the logger
    logger.addHandler(fh)
    return logger

def seestar_run_runner(targetName, coords, exptime, totaltime):
    # Get the path to the seestar_run.py script
    seestar_run_path = os.path.join(os.path.dirname(__file__), 'seestar_emul.py')
    # Check if the seestar_run.py script exists
    if not os.path.exists(seestar_run_path):
        logger.error('seestar_run.py does not exist')
        return 1
    # Check if the targetName is a string
    if not isinstance(targetName, str):
        logger.error('targetName is not a string')
        return 1
    # Check if the coords is a list
    if not isinstance(coords, list):
        logger.error('coords is not a list')
        return 1
    # Check if the coords list has two elements
    if len(coords) != 2:
        logger.error('coords does not have two elements')
        return 1
    # Check if the first element of the coords list is a number
    if not isinstance(coords[0], (int, float, np.float64)):
        logger.error('first element of coords is not a number')
        return 1
    # Check if the second element of the coords list is a number
    if not isinstance(coords[1], (int, float, np.float64)):
        logger.error('second element of coords is not a number')
        return 1
    # Check if the exptime is a number  
    if not isinstance(exptime, (int, float, np.float64)):
        logger.error(f'exptime is not a number:  {exptime}')
        return 1
    # Check if the totaltime is a number
    if not isinstance(totaltime, (int, float, np.float64)):
        logger.error(f'totaltime is not a number:  {totaltime}')
        return 1
    # write to log file
    logger.info(f'Run {targetName} {coords} {exptime} {totaltime}')
    # Run the seestar_run.py script
    p = subprocess.Popen(['python', seestar_run_path, targetName, str(coords[0]), str(coords[1]), str(exptime), str(totaltime)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #check the return value of the seestar_run.py script
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error
        ('seestar_run.py failed')
        logger.error(stderr.decode('utf-8'))
        return 1
    logger.debug(stdout.decode('utf-8')[:-1] + ' Success')
    return 0

def get_coord_object(target_names):
    """
    Get the coordinates of the target names from the Simbad database.
    Args:
        target_names (list): A list of target names.
    Returns:
        tuple: A tuple of two numpy arrays containing the right ascension and declination of the target names.
    """
    try:
        result_table = Simbad.query_objects(target_names)
        object_ra = result_table['RA'].data  # Right Ascension
        object_dec = result_table['DEC'].data  # Declination
        coord=SkyCoord(object_ra, object_dec,unit=(u.deg))
    except Exception as e:
        logger.error(f'Unable to get coordinates from Simbad - {e}')
        raise RuntimeError('Unable to get coordinates from Simbad')
    return coord.ra.deg, coord.dec.deg


def target_session():
    """
    Run a session of observations on a list of targets.
    """
    global logger
    global ras
    global decs
    global repeat
    global mode
    global targetList
    global target_stack_times
    global target_exptimes
    global target_names
 
    # Loop through the targets
    for i in range(len(ras)):
        if repeat:
            # Loop through the targets
            for i in range(len(ras)):
                exit_status = seestar_run_runner(target_names[i], [ras[i], decs[i]], target_exptimes[i], target_stack_times[i])
                logger.debug(f'Exit status for target {target_names[i]}: {exit_status}')
                if exit_status != 0:
                    logger.error(f'Error running target {target_names[i]}')
                    raise RuntimeError('Error running target')
        else:
            exit_status = seestar_run_runner(target_names[i], [ras[i], decs[i]], target_exptimes[i], target_stack_times[i])
            logger.debug(f'Exit status for target {target_names[i]}: {exit_status}')
            if exit_status != 0:
                logger.error(f'Error running target {target_names[i]}')
                raise RuntimeError('Error running target')
    logger.info('Session complete')        
    return 0

if __name__ == '__main__':
    logger = logger()
    # parse arguments from the command line with our own parser
    parser = argparse.ArgumentParser(description='Seestar Varstar')
    parser.add_argument('schedule_file', type=str, help='The name of the target list file')
    parser.add_argument('mode', type=str, help='The mode of operation: single or repeat')
    args = parser.parse_args()
    targetList = args.schedule_file
    mode =  args.mode
    logger.info(f'Arguments: {targetList, mode}')

    # Get the schedule of targets
    try:
        target_df = pd.read_csv(targetList)
        target_df['TotalExp'] = target_df['TotalExp'].astype(float)
        target_df['ExpTime'] = target_df['ExpTime'].astype(float)
    except Exception as e:
        logger.error(f'Unable to load schedule - {e}')
        raise RuntimeError('Unable to load schedule')
    target_names=target_df['Name'].values
    target_stack_times = target_df['TotalExp'].values
    target_exptimes = target_df['ExpTime'].values

    ras,decs = get_coord_object(target_names)
    logger.debug(f'list of targets {target_names, ras, decs}')
    # determine the repetition pattern requested
    if (mode not in ['repeat', 'single']):
        logger.error(f'target sequence mode not known: {mode}')
        raise RuntimeError('Sequence mode not known')
    elif (mode == 'repeat'):
            logger.info(f'Targets ({len(ras)}) will be cycled repeatedly until dawn - mode {mode}')
            repeat = True
    elif (mode == 'single'):
            logger.info(f'Targets ({len(ras)}) will be observed in order - mode {mode}')
            repeat = False        

    # Run the target session
    target_session()
