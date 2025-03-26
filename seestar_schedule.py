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

def create_schedule(file):
    gain = 80
    targets = read_targets(file)
    # generate the json schedule using the json format above
    schedule = {}
    schedule['version'] = 1.0
    schedule['Event'] = 'Scheduler'
    schedule['schedule_id'] = str(uuid.uuid1())
    schedule['list'] = []

    # for each target in the target list, create a schedule item
    for i in range(len(targets)):
        target_name = targets['Name'][i]
        exptime = targets['ExpTime'][i]    
        totalexp = targets['TotalExp'][i]
        ra = targets['ra'][i]
        dec = targets['dec'][i]

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

    # print the json schedule to the console
   # print(json.dump(schedule, default=lambda x: int(x) if isinstance(x, (np.integer, np.int64)) else x))
   # to the sscreen not a file
    print(json.dumps(schedule, default=lambda x: int(x) if isinstance(x, (np.integer, np.int64)) else x))

def read_targets(file):
    # read in the demo targets as a df
    targets = pd.read_csv(file)
    # resolve their coordinates using astroquery call to Simbad 
    # and add them to the df
    coords = []
    for i in range(len(targets)):
        target = targets['Name'][i]
        result_table = Simbad.query_object(target)
        coords.append(SkyCoord(ra=result_table['ra'][0], dec=result_table['dec'][0], unit=(u.hourangle, u.deg)))
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