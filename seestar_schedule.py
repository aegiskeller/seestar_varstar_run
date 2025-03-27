# seestar needs the following json to form the schedule:
# 
# {
#     "version": 1.0,
#     "Event": "Scheduler",
#     "schedule_id": "faecb0b0-1f1b-11e9-8b4f-0a580a8100e0",
#     "list": [
#         {
#             "action": "start_mosaic",
#             "params": {
#                 "target_name": "M51",
#                 "is_j2000": true,
#                 "ra": "13h28m53.0s",
#                 "dec": "47d11m42.0s",
#                 "is_use_lp_filter": false,
#                 "panel_time_sec": 300,
#                 "ra_num": 1,
#                 "dec_num": 1,
#                 "panel_overlap_percent": 100,
#                 "selected_panels": "",
#                 "gain": 80,
#                 "is_use_autofocus": false,
#                 "num_tries": 3,
#                 "retry_wait_s": 10
#             },
#             "schedule_item_id": "faecb0b0-1f1b-11e9-8b4f-0a580a8100e0"
#         },
#         {
#             "action": "wait_for",
#             "params": {
#                 "time_sec": 300
#             },
#             "schedule_item_id": "faecb0b0-1f1b-11e9-8b4f-0a580a8100e0"
#         }
#     ],
#     "state": "stopped",
#     "is_stacking_paused": false,
#     "is_stacking": false,
#     "is_skip_requested": false,
#     "current_item_id": "",
#     "item_number": 0
# }
# the startup sequence is a list item as follows:
# {
#     "action": "wait_until",
#     "params": {
#         "local_time": "20:00"
#     },
#     "schedule_item_id": "faecb0b0-1f1b-11e9-8b4f-0a580a8100e0"
# }

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


def local_twilight():
    # get the current date
    now = datetime.datetime.now(tz=pytz.utc)
    # get the current date
    today = now.date()
    #use pyephem to calculate the local twilight times
    obs = ephem.Observer()
    obs.lat = '-35.4'    # lat of the observatory
    obs.long = '149.0'    # long of the observatory
    obs.date = today
    # calculate the next nautical twilight
    # nautical twilight is when the sun is 12 degrees below the horizon
    # determine when the sun is 12 degrees below the horizon
    obs.horizon = '-12'
    nautical_twilight = obs.next_setting(ephem.Sun(), use_center=True).datetime()
    local_tz = pytz.timezone('Australia/Sydney')
    # calculate the next morning nautical twilight
    morning_nautical_twilight = obs.next_rising(ephem.Sun(), use_center=True).datetime()
    ntlocal = nautical_twilight.replace(tzinfo=pytz.utc).astimezone(local_tz)
    mntlocal = morning_nautical_twilight.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return ntlocal, mntlocal

def create_schedule(file):
    gain = 80
    targets = read_targets(file)
    # generate the json schedule using the json format above
    schedule = {}
    schedule['version'] = 1.0
    schedule['Event'] = 'Scheduler'
    # generate a unique schedule id using uuid
    schedule['schedule_id'] = str(uuid.uuid1())
    schedule['list'] = []
    # add a wait_until item to the schedule to wait until nautical twilight
    nautical_twilight, morning_nautical_twilight = local_twilight()
    wait_until_item = {}
    wait_until_item['action'] = 'wait_until'
    wait_until_item['params'] = {}
    wait_until_item['params']['local_time'] = nautical_twilight.strftime('%H:%M')
    wait_until_item['schedule_item_id'] = str(uuid.uuid1())
    schedule['list'].append(wait_until_item)
    # add a start_up_sequence item to the schedule
    start_up_sequence = {}
    start_up_sequence['action'] = 'start_up_sequence'
    start_up_sequence['params'] = {}
    start_up_sequence['params']['auto_focus'] = True
    start_up_sequence['params']['dark_frames'] = True
    start_up_sequence['params']['3ppa'] = True
    start_up_sequence['params']['raise_arm'] = True
    start_up_sequence['schedule_item_id'] = str(uuid.uuid1())
    schedule['list'].append(start_up_sequence)

    elapsed_time = 0
    # for each target in the target list, create a schedule item
    for i in range(len(targets)):
        target_name = targets['Name'][i]
        exptime = targets['ExpTime'][i]    
        totalexp = targets['TotalExp'][i]
        # convert the ra and dec from degress to hours and degrees
        print (targets['ra'][i])
        print (targets['dec'][i])
        ra = targets['ra'][i] / 15
        dec = targets['dec'][i]
        # fomrat the ra and dec as strings
        rah = str(int(ra))
        ramin = str(int((ra - int(ra)) * 60))
        rasec = str(int((ra - int(ra) - int((ra - int(ra))) * 60) * 60))
        decd = str(int(dec))
        decmin = str(abs(int((dec - int(dec)) * 60)))
        decsec = str(abs(int((dec - int(dec) - int((dec - int(dec))) * 60) * 60)))
        # pad the minutes and seconds with zeros
        if len(ramin) == 1:
            ramin = '0' + ramin
        if len(rasec) == 1:
            rasec = '0' + rasec
        if len(decmin) == 1:
            decmin = '0' + decmin
        if len(decsec) == 1:
            decsec = '0' + decsec  
        ra = rah + 'h' + ramin + 'm' + rasec + 's'
        dec = decd + 'd' + decmin + 'm' + decsec + 's'
        pause = targets['Pause'][i]
        # we set the exposure time for each target 
        set_exposure_time = {}
        set_exposure_time['action'] = 'action_set_exposure'
        set_exposure_time['params'] = {}
        set_exposure_time['params']['exp'] = exptime * 1000 # convert to ms
        set_exposure_time['schedule_item_id'] = str(uuid.uuid1())
        schedule['list'].append(set_exposure_time)

        # Initialize a new schedule_item for each target
        schedule_item = {}
        schedule_item['action'] = 'start_mosaic'
        schedule_item['params'] = {}
        schedule_item['params']['target_name'] = target_name
        schedule_item['params']['is_j2000'] = True
        schedule_item['params']['ra'] = ra
        schedule_item['params']['dec'] = dec
        schedule_item['params']['is_use_lp_filter'] = False
        schedule_item['params']['panel_time_sec'] = totalexp
        schedule_item['params']['ra_num'] = 1
        schedule_item['params']['dec_num'] = 1
        schedule_item['params']['panel_overlap_percent'] = 100
        schedule_item['params']['selected_panels'] = ''
        schedule_item['params']['gain'] = gain
        schedule_item['params']['is_use_autofocus'] = False
        schedule_item['params']['num_tries'] = 3
        schedule_item['params']['retry_wait_s'] = 10
        schedule_item['schedule_item_id'] = str(uuid.uuid1())
        schedule['list'].append(schedule_item)
        elapsed_time += totalexp
    # add a wait_for item to the schedule between each target
        if pause > 0:
            wait_item = {}
            wait_item['action'] = 'wait_for'
            wait_item['params'] = {}
            wait_item['params']['timer_sec'] = pause
            wait_item['schedule_item_id'] = str(uuid.uuid1())
            schedule['list'].append(wait_item)
            elapsed_time += pause
    # add the final state of the schedule
    schedule['state'] = 'stopped'
    schedule['is_stacking_paused'] = False
    schedule['is_stacking'] = False
    schedule['is_skip_requested'] = False
    schedule['current_item_id'] = ''
    schedule['item_number'] = 0

    # determine the local time that the schedule will finish 
    # add the elapsed time to the nautical twilight time in the local timezone
    print('The schedule will start at: ', nautical_twilight)
    finish_time = nautical_twilight + datetime.timedelta(seconds=int(elapsed_time))
    print('The schedule will finish at: ', finish_time)
    # determine if the schedule will finish before morning nautical twilight
    if finish_time > morning_nautical_twilight:
        print('The schedule will finish after morning nautical twilight')
    else:
        print('The schedule will finish before morning nautical twilight')
        # determine the time from the finish of the schedule and morning nautical twilight
        time_to_morning_nautical_twilight = morning_nautical_twilight - finish_time
        # print this in a red color
        print('The time to morning nautical twilight is: ', time_to_morning_nautical_twilight)

    # write the schedule to a json file
    with open('schedule.json', 'w') as f:
        f.write(json.dumps(schedule, indent=4, default=lambda x: int(x) if isinstance(x, (np.integer, np.int64)) else x))
    # print the schedule to the console
#    print(json.dumps(schedule, indent=4, default=lambda x: int(x) if isinstance(x, (np.integer, np.int64)) else x))

def read_targets(file):
    # read in the demo targets as a df
    targets = pd.read_csv(file)
    # resolve their coordinates using astroquery call to Simbad 
    # and add them to the df
    coords = []
    for i in range(len(targets)):
        target = targets['Name'][i]
        result_table = Simbad.query_object(target)
        coords.append(SkyCoord(ra=result_table['ra'][0], dec=result_table['dec'][0], unit=(u.deg, u.deg)))

    targets['ra'] = [coord.ra.deg for coord in coords]
    targets['dec'] = [coord.dec.deg for coord in coords ]
    return targets


if __name__ == '__main__':
    # read in the target list name as an argument
    target_file = sys.argv[1]
    if target_file == '':
        print('Please provide a target name')
        sys.exit()
    if target_file not in os.listdir():
        print('The target file does not exist')
        sys.exit()
    create_schedule(target_file)