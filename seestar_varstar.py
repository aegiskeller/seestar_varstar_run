import os
import subprocess
import numpy as np
import pandas as pd
import seestar_varstar_params as sp
import logging
import argparse
from astropy.coordinates import SkyCoord
from astropy import units as u
from astroquery.simbad import Simbad
import datetime
from datetime import timezone
import ephem
import time
import pytz
import requests

global logger
global test
global testvarstar


def logger():
    # Create a logger
    logger = logging.getLogger("seestar_varstar")
    logger.setLevel(logging.DEBUG)
    # Create a file handler
    fh = logging.FileHandler("seestar_varstar.log")
    fh.setLevel(logging.DEBUG)
    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # Add the formatter to the file handler
    fh.setFormatter(formatter)
    # Add the file handler to the logger
    logger.addHandler(fh)
    # Create a console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # Add the formatter to the console handler
    ch.setFormatter(formatter)
    # Add the console handler to the logger
    logger.addHandler(ch)
    return logger


def determine_twilight():
    """
    Determine the start and end times of astronomical twilight
    """
    # Get the current time using utc tz
    now = datetime.datetime.now(tz=pytz.utc)
    # Get the astronomical twilight start and end times
    # use pyEphem to calculate the astronomical twilight times
    # for the current date and location
    # Get the astronomical twilight start and end times
    obs = ephem.Observer()
    latitude = sp.Latitude
    longitude = sp.Longitude
    obs.lat = str(latitude)
    obs.lon = str(longitude)
    obs.elev = sp.Elevation
    # specify the date as today in utc
    obs.date = now.strftime("%Y-%m-%d")
    # use the sun object to calculate the twilight times
    sun = ephem.Sun()
    obs.horizon = "-18"
    start = obs.next_rising(sun, use_center=True).datetime()
    end = obs.next_setting(sun, use_center=True).datetime()
    logger.debug(f"Current UTC: {now}")
    local_tz = pytz.timezone(sp.tz)
    sunrise_local = start.replace(tzinfo=pytz.utc).astimezone(local_tz)
    sunset_local = end.replace(tzinfo=pytz.utc).astimezone(local_tz)
    sunrise_utc = start.replace(tzinfo=pytz.utc).astimezone(pytz.utc)
    sunset_utc = end.replace(tzinfo=pytz.utc).astimezone(pytz.utc)
    logger.debug(f'Sunrise UTC: {sunrise_utc.strftime("%Y-%m-%d %H:%M:%S %Z")}')
    logger.debug(f'Sunset UTC: {sunset_utc.strftime("%Y-%m-%d %H:%M:%S %Z")}')
    logger.debug(f'Sunset: {sunset_local.strftime("%Y-%m-%d %H:%M:%S %Z")}')
    logger.debug(f'Sunrise: {sunrise_local.strftime("%Y-%m-%d %H:%M:%S %Z")}')
    return sunrise_local, sunset_local


def seestar_run_runner(targetName, coords, exptime, totaltime):
    global test
    global testvarstar
    # Get the path to the seestar_run.py script
    if test and not testvarstar:
        seestar_run_path = os.path.join(os.path.dirname(__file__), "seestar_emul.py")
    else:
        seestar_run_path = os.path.join(os.path.dirname(__file__), "seestar_run.py")
    # Check if the seestar_run.py script exists
    if not os.path.exists(seestar_run_path):
        logger.error("seestar_run.py does not exist")
        return 1
    # Check if the targetName is a string
    if not isinstance(targetName, str):
        logger.error("targetName is not a string")
        return 1
    # Check if the coords is a list
    if not isinstance(coords, list):
        logger.error("coords is not a list")
        return 1
    # Check if the coords list has two elements
    if len(coords) != 2:
        logger.error("coords does not have two elements")
        return 1
    # Check if the first element of the coords list is a number
    if not isinstance(coords[0], (int, float, np.float64)):
        logger.error("first element of coords is not a number")
        return 1
    # Check if the second element of the coords list is a number
    if not isinstance(coords[1], (int, float, np.float64)):
        logger.error("second element of coords is not a number")
        return 1
    # Check if the exptime is a number
    if not isinstance(exptime, (int, float, np.float64)):
        logger.error(f"exptime is not a number:  {exptime}")
        return 1
    # Check if the totaltime is a number
    if not isinstance(totaltime, (int, float, np.float64)):
        logger.error(f"totaltime is not a number:  {totaltime}")
        return 1
    # write to log file
    logger.info(f"Run {targetName} {coords} {exptime} {totaltime}")
    # Run the seestar_run.py script
    p = subprocess.Popen(
        [
            "python",
            seestar_run_path,
            targetName,
            str(coords[0]),
            str(coords[1]),
            str(exptime),
            str(totaltime),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # check the return value of the seestar_run.py script
    stdout, stderr = p.communicate()
    logger.debug(f"stdout: {stdout}")
    logger.debug(f"stderr: {stderr}")
    if p.returncode != 0:
        logger.error
        ("seestar_run.py failed")
        logger.error(stderr.decode("utf-8"))
        return 1
    logger.debug(stdout.decode("utf-8")[:-1] + " Success")
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
        object_ra = result_table["RA"].data  # Right Ascension
        object_dec = result_table["DEC"].data  # Declination
        coord = SkyCoord(object_ra, object_dec, unit=(u.deg))
    except:
        logger.debug("Unable to get coordinates from Simbad with caps")
        try:
            object_ra = result_table["ra"].data  # Right Ascension
            object_dec = result_table["dec"].data  # Declination
            coord = SkyCoord(object_ra, object_dec, unit=(u.deg))
        except Exception as e:
            logger.error(f"Unable to get coordinates from Simbad - {e}")
            raise RuntimeError("Unable to get coordinates from Simbad")
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

    # first check if it is okay to observe
    # Get the start and end times of astronomical twilight in local time
    sunrise, sunset = determine_twilight()
    iamearly = True
    while iamearly:
        # Check if the current time is within the astronomical twilight
        now = datetime.datetime.now(pytz.timezone(sp.tz))
        if now > sunrise and not (test or testvarstar):
            logger.error(
                f'Current time is too late to observe - past sunrise{sunrise.strftime("%H:%M")}'
            )
            return 1
        # Check if the current time is before the astronomical twilight
        if now < sunset and not (test or testvarstar):
            logger.info(
                f'Current time is too early to observe. Waiting until {sunset.strftime("%H:%M")} (now: {now.strftime("%H:%M")})'
            )
            time.sleep(60)
        else:
            iamearly = False
    logger.info("Starting observations")

    # Loop through the targets
    for i in range(len(ras)):
        # check the current time and see if it is in the twilight zone
        now = datetime.datetime.now(pytz.timezone(sp.tz))
        if now > sunrise and not test:
            logger.error("Current time is too late to observe")
            return 1
        if repeat:
            # Loop through the targets
            for i in range(len(ras)):
                exit_status = seestar_run_runner(
                    target_names[i],
                    [ras[i], decs[i]],
                    target_exptimes[i],
                    target_stack_times[i],
                )
                logger.debug(f"Exit status for target {target_names[i]}: {exit_status}")
                if exit_status != 0:
                    logger.error(f"Error running target {target_names[i]}")
                    # raise RuntimeError('Error running target')
        else:
            exit_status = seestar_run_runner(
                target_names[i],
                [ras[i], decs[i]],
                target_exptimes[i],
                target_stack_times[i],
            )
            logger.debug(f"Exit status for target {target_names[i]}: {exit_status}")
            if exit_status != 0:
                logger.error(f"Error running target {target_names[i]}")
                # raise RuntimeError('Error running target')
    logger.info("Session complete")
    return 0


if __name__ == "__main__":
    logger = logger()
    # parse arguments from the command line with our own parser
    parser = argparse.ArgumentParser(description="Seestar Varstar")
    parser.add_argument(
        "schedule_file", type=str, help="The name of the target list file"
    )
    parser.add_argument(
        "mode", type=str, help="The mode of operation: single or repeat"
    )
    # add an optional argument for the testing mode with default of False
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    # add an optional argument for a testing mode 'testvarstar' with default of False
    parser.add_argument(
        "--testvarstar", action="store_true", help="Run in test mode with the seestar"
    )
    args = parser.parse_args()
    targetList = args.schedule_file
    mode = args.mode
    test = args.test
    testvarstar = args.testvarstar
    logger.info(f"Arguments: {targetList, mode, test, testvarstar}")
    # Get the schedule of targets
    try:
        target_df = pd.read_csv(targetList)
        target_df["TotalExp"] = target_df["TotalExp"].astype(float)
        target_df["ExpTime"] = target_df["ExpTime"].astype(float)
    except Exception as e:
        logger.error(f"Unable to load schedule - {e}")
        raise RuntimeError("Unable to load schedule")
    target_names = target_df["Name"].values
    target_stack_times = target_df["TotalExp"].values
    target_exptimes = target_df["ExpTime"].values

    ras, decs = get_coord_object(target_names)
    # get the number of targets and change a str targets to equal 'target' if one target
    if len(ras) == 1:
        targetstr = "Target"
    else:
        targetstr = "Targets"
    logger.debug(f"list of {targetstr, target_names, ras, decs}")
    # determine the repetition pattern requested
    if mode not in ["repeat", "single"]:
        logger.error(f"{targetstr} sequence mode not known: {mode}")
        raise RuntimeError("Sequence mode not known")
    elif mode == "repeat":
        logger.info(
            f"{targetstr} ({len(ras)}) will be cycled repeatedly until dawn - mode {mode}"
        )
        repeat = True
    elif mode == "single":
        logger.info(f"{targetstr} ({len(ras)}) will be observed in order - mode {mode}")
        repeat = False
    # check the return value of the target_session function
    exit_status = target_session()
    if exit_status != 0:
        logger.error("Error running target session")
        raise RuntimeError("Error running target session")
    logger.info("Program complete")
    exit(0)
