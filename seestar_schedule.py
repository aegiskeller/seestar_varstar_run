import json
import datetime
import pandas as pd
import numpy as np
import os
import sys
import uuid
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad
import ephem
import pytz
from colorama import Fore, Back, Style


def local_twilight(obs_params):
    """
    Calculate the local twilight times
    :param obs_params: the observatory parameters
    :return: the local twilight times
    """
    # get the current date
    now = datetime.datetime.now(tz=pytz.utc)
    # get the current date
    today = now.date()
    # use pyephem to calculate the local twilight times
    obs = ephem.Observer()
    # set the observatory parameters from the obs_params
    # print (obs_params)
    obs.lat = obs_params["Latitude"]
    obs.long = obs_params["Longitude"]
    obs.elevation = float(obs_params["Elevation"])
    obs.date = today
    # calculate the next nautical twilight
    # nautical twilight is when the sun is 12 degrees below the horizon
    # determine when the sun is 12 degrees below the horizon
    obs.horizon = "-12"
    nautical_twilight = obs.next_setting(ephem.Sun(), use_center=True).datetime()
    local_tz = pytz.timezone(obs_params["Timezone"])
    # calculate the next morning nautical twilight
    morning_nautical_twilight = obs.next_rising(ephem.Sun(), use_center=True).datetime()
    ntlocal = nautical_twilight.replace(tzinfo=pytz.utc).astimezone(local_tz)
    mntlocal = morning_nautical_twilight.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return ntlocal, mntlocal


def create_schedule(file, obs_params, config_settings):
    """
    Create a schedule from a target list
    :param file: the target list file
    :param obs_params: the observatory parameters
    :param config_settings: the config settings
    :return: None
    """
    gain = 80
    targets = read_targets(file)
    # generate the json schedule using the json format above
    schedule = {}
    schedule["version"] = 1.0
    schedule["Event"] = "Scheduler"
    # generate a unique schedule id using uuid
    schedule["schedule_id"] = str(uuid.uuid1())
    schedule["list"] = []
    nautical_twilight, morning_nautical_twilight = local_twilight(obs_params)
    if config_settings["Wait_For_Twilight"] == "True":
        # add a wait_until item to the schedule to wait until nautical twilight
        wait_until_item = {}
        wait_until_item["action"] = "wait_until"
        wait_until_item["params"] = {}
        wait_until_item["params"]["local_time"] = nautical_twilight.strftime("%H:%M")
        wait_until_item["schedule_item_id"] = str(uuid.uuid1())
        schedule["list"].append(wait_until_item)
    if config_settings["Start_Up_Sequence"] == "True":
        # add a start_up_sequence item to the schedule
        start_up_sequence = {}
        start_up_sequence["action"] = "start_up_sequence"
        start_up_sequence["params"] = {}
        start_up_sequence["params"]["auto_focus"] = True
        start_up_sequence["params"]["dark_frames"] = True
        start_up_sequence["params"]["3ppa"] = True
        start_up_sequence["params"]["raise_arm"] = True
        start_up_sequence["schedule_item_id"] = str(uuid.uuid1())
        schedule["list"].append(start_up_sequence)

    elapsed_time = 0
    # if the schedule flag Repeat_Target is set to True, then repeat the target list
    irepeat = True
    while irepeat:
        ixgt2 = 0
        # for each target in the target list, create a schedule item
        for i in range(len(targets)):
            target_name = targets["Name"][i]
            exptime = targets["ExpTime"][i]
            totalexp = targets["TotalExp"][i]
            ra = targets["ra"][i]
            dec = targets["dec"][i]
            # check the altitude of the target
            obs = ephem.Observer()
            obs.lat = obs_params["Latitude"]
            obs.long = obs_params["Longitude"]
            obs.elevation = float(obs_params["Elevation"])
            # calulate the time of the observation as the nautical twilight time plus the elapsed time
            # convert nautical_twilight to UTC
            date = nautical_twilight.astimezone(pytz.utc) + datetime.timedelta(
                seconds=int(elapsed_time)
            )
            # convert to a pyephem date
            obs.date = date
            target = ephem.FixedBody()
            target._ra = ra
            target._dec = dec
            target.compute(obs)
            alt = target.alt
            az = target.az
            # use module to print to the terminal in color
            print(
                Fore.BLUE
                + f"Target {target_name} has altitude {alt} and azimuth {az}"
                + Style.RESET_ALL
            )
            # check if the target has set below 30 degrees altitude and is in the west
            if float(alt) < 30 / 180 * ephem.pi and az > 180 / 180 * ephem.pi:
                print(
                    Fore.RED
                    + f"{target_name} below 30 degrees altitude and is in the west"
                    + Style.RESET_ALL
                )
                ixgt2 += 1
                continue
            # check if the observation would take us past morning twilight
            if (
                nautical_twilight
                + datetime.timedelta(seconds=int(elapsed_time))
                + datetime.timedelta(seconds=int(totalexp))
                > morning_nautical_twilight
            ):
                irepeat = False
                break
            pause = targets["Pause"][i]
            # we set the exposure time for each target
            set_exposure_time = {}
            set_exposure_time["action"] = "action_set_exposure"
            set_exposure_time["params"] = {}
            set_exposure_time["params"]["exp"] = exptime * 1000  # convert to ms
            set_exposure_time["schedule_item_id"] = str(uuid.uuid1())
            schedule["list"].append(set_exposure_time)

            # Initialize a new schedule_item for each target
            schedule_item = {}
            schedule_item["action"] = "start_mosaic"
            schedule_item["params"] = {}
            schedule_item["params"]["target_name"] = target_name
            schedule_item["params"]["is_j2000"] = True
            schedule_item["params"]["ra"] = ra
            schedule_item["params"]["dec"] = dec
            schedule_item["params"]["is_use_lp_filter"] = False
            schedule_item["params"]["panel_time_sec"] = totalexp
            schedule_item["params"]["ra_num"] = 1
            schedule_item["params"]["dec_num"] = 1
            schedule_item["params"]["panel_overlap_percent"] = 100
            schedule_item["params"]["selected_panels"] = ""
            schedule_item["params"]["gain"] = gain
            schedule_item["params"]["is_use_autofocus"] = False
            schedule_item["params"]["num_tries"] = 3
            schedule_item["params"]["retry_wait_s"] = 10
            schedule_item["schedule_item_id"] = str(uuid.uuid1())
            schedule["list"].append(schedule_item)
            elapsed_time += totalexp
            # add a wait_for item to the schedule between each target
            if pause > 0:
                wait_item = {}
                wait_item["action"] = "wait_for"
                wait_item["params"] = {}
                wait_item["params"]["timer_sec"] = pause
                wait_item["schedule_item_id"] = str(uuid.uuid1())
                schedule["list"].append(wait_item)
                elapsed_time += pause
        # if the Repeat_Targets flag is set to False, then we are done
        if config_settings["Repeat_Targets"] == "False":
            irepeat = False
        # if all the targets are above 2 airmasses, then we are done
        if ixgt2 == len(targets):
            print(
                Fore.RED
                + "All targets are above 2 airmasses - exiting"
                + Style.RESET_ALL
            )
            irepeat = False

    # add the final state of the schedule
    schedule["state"] = "stopped"
    schedule["is_stacking_paused"] = False
    schedule["is_stacking"] = False
    schedule["is_skip_requested"] = False
    schedule["current_item_id"] = ""
    schedule["item_number"] = 0

    # determine the local time that the schedule will finish
    # add the elapsed time to the nautical twilight time in the local timezone
    print("The schedule will start at: ", nautical_twilight)
    finish_time = nautical_twilight + datetime.timedelta(seconds=int(elapsed_time))
    print("The schedule will finish at: ", finish_time)
    # determine if the schedule will finish before morning nautical twilight
    if finish_time > morning_nautical_twilight:
        print("The schedule will finish after morning nautical twilight")
    else:
        print("The schedule will finish before morning nautical twilight")
        # determine the time from the finish of the schedule and morning nautical twilight
        time_to_morning_nautical_twilight = morning_nautical_twilight - finish_time
        # print this in a red color
        print(
            "The time to morning nautical twilight is: ",
            time_to_morning_nautical_twilight,
        )

    # write the schedule to a json file
    with open("schedule.json", "w") as f:
        f.write(
            json.dumps(
                schedule,
                indent=4,
                default=lambda x: (
                    int(x) if isinstance(x, (np.integer, np.int64)) else x
                ),
            )
        )
    # print the schedule to the console


#    print(json.dumps(schedule, indent=4, default=lambda x: int(x) if isinstance(x, (np.integer, np.int64)) else x))


def read_targets(file):
    # read in the targets from the target file
    # first we read the target file in until we find the start of the target list
    with open(file, "r") as f:
        lines = f.readlines()
    # find the start of the target list
    # the target list starts with the line 'Name,ExpTime,TotalExp,Pause'
    for i in range(len(lines)):
        if lines[i].startswith("Name"):
            target_start = i
            break
    # create a dataframe from the target list
    # set the column names to the first row of the target list
    targets = pd.read_csv(file, skiprows=target_start)
    targets.columns = lines[target_start].replace(" ", "").strip().split(",")
    # read in the target list
    # resolve their coordinates using astroquery call to Simbad
    # and add them to the df
    coords = []
    for i in range(len(targets)):
        target = targets["Name"][i]
        result_table = Simbad.query_object(target)
        if result_table is not None:
            ra = result_table["ra"][0] / 15
            dec = result_table["dec"][0]
            # convert the float ra to a string with the format hh:mm:ss
            rah = int(ra)
            ramin = int((ra - rah) * 60)
            rasec = (ra - rah - ramin / 60) * 3600
            ra = f"{rah:02}:{ramin:02}:{rasec:04.1f}"
            # convert the float dec to a string with the format dd:mm:ss
            decd = int(dec)
            decmin = int((dec - decd) * 60)
            decsec = (dec - decd - decmin / 60) * 3600
            # construct the dec string with padding of 0s to 2 digits
            dec = f"{decd:+03}:{abs(decmin):02}:{abs(decsec):04.1f}"
            coords.append((ra, dec))
    # add the coordinates to the dataframe
    coords = pd.DataFrame(coords, columns=["ra", "dec"])
    targets = pd.concat([targets, coords], axis=1)
    # print(targets)
    return targets


if __name__ == "__main__":
    # read in the target list name as an argument
    target_file = sys.argv[1]
    if target_file == "":
        print("Please provide a target name")
        sys.exit()
    if target_file not in os.listdir():
        print("The target file does not exist")
        sys.exit()
    # read in the observatory parameters from the target_file
    with open(target_file, "r") as f:
        lines = f.readlines()
    for i in range(len(lines)):
        if lines[i].startswith("Observatory"):
            obs_line = i
            break
    # read the lines forward from the Observatory line to get the observatory parameters
    obs_params = {}
    for i in range(obs_line + 1, len(lines)):
        if lines[i].startswith("Config") or lines[i].strip() == "":
            break
        key, value = lines[i].split(":", 1)
        value = value.strip()
        obs_params[key.strip()] = (
            value.strip()
        )  # Strip whitespace and newline characters
        # read in the config settings form the target file
    for i in range(len(lines)):
        if lines[i].startswith("Config"):
            config_line = i
            break
    # read the lines forward from the Config line to get the config settings
    config_settings = {}
    for i in range(config_line + 1, len(lines)):
        if lines[i].startswith("Targets") or lines[i].strip() == "":
            break
        key, value = lines[i].split(":")
        config_settings[key] = value

    create_schedule(target_file, obs_params, config_settings)
    print(Fore.GREEN + "Schedule created" + Style.RESET_ALL)
    print("The schedule has been written to schedule.json")
