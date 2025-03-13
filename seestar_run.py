import socket
import json
import time
from datetime import datetime
import threading
import sys
import argparse
import seestar_varstar_params as sp
import logging

#declare the logger globally
logger = None

def CreateLogger():
    # Create a custom logger 
    logger = logging.getLogger('seestar_run')
    logger.setLevel(logging.DEBUG)

    # Create handlers
    #console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler('seestar_run.log')

    # Set levels for handlers
    #console_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters and add them to handlers
    #console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    #console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    # Add handlers to the logger
    #logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return(logger)

def heartbeat(): #I noticed a lot of pairs of test_connection followed by a get if nothing was going on
    json_message("test_connection")
#    json_message("scope_get_equ_coord")

def json_message2(data, logger):
    if data:
        json_data = json.dumps(data)
        logger.debug("Sending2 %s" % json_data)
        resp = send_message(json_data + "\r\n")
        logger.debug("Response2: %s" % resp)
        return resp
    else:
        return None

def shutdown_seestar(logger,cmdid):
    """
    Shutdown the seestar device
    """
    data = {}
    data['id'] = cmdid
    cmdid+=1
    data['method'] = 'pi_shutdown'
    json_message2(data,logger)

def set_stack_settings(logger,cmdid):
    logger.debug("set stack setting to record individual frames")
    data = {}
    data['id'] = cmdid
    cmdid += 1
    data['method'] = 'set_stack_setting'
    params = {}
    params['save_discrete_frame'] = True
    data['params'] = params
    return(json_message2(data,logger))


def send_message(data):
    global s
    try:
        s.sendall(data.encode())  # TODO: would utf-8 or unicode_escaped help here
    except socket.error as e:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        send_message(data)

def get_socket_msg():
    global s
    try:
        data = s.recv(1024 * 60)  # comet data is >50kb
    except socket.error as e:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        data = s.recv(1024 * 60)
    data = data.decode("utf-8")
    if is_debug:
        print("Received :", data)
    return data
    
def receieve_message_thread_fn():
    global is_watch_events
    global op_state
    global s
    global logger
        
    msg_remainder = ""
    while is_watch_events:
        #print("checking for msg")
        data = get_socket_msg()
        if data:
            msg_remainder += data
            first_index = msg_remainder.find("\r\n")
            
            while first_index >= 0:
                first_msg = msg_remainder[0:first_index]
                msg_remainder = msg_remainder[first_index+2:]            
                parsed_data = json.loads(first_msg)
                
                if 'Event' in parsed_data and parsed_data['Event'] == "AutoGoto":
                    state = parsed_data['state']
                    logger.debug("AutoGoto state: %s" % state)
                    if state == "complete" or state == "fail":
                        op_state = state
                
                if is_debug:
                    logger.debug(parsed_data)
                    
                first_index = msg_remainder.find("\r\n")
        time.sleep(1)

def json_message(instruction):
    global cmdid
    global logger
    data = {"id": cmdid, "method": instruction}
    cmdid += 1
    json_data = json.dumps(data)
    if is_debug:
        logger.debug("Sending %s" % json_data)
    send_message(json_data+"\r\n")


def goto_target(ra, dec, target_name, exp_time=10, exp_cont=60):
    """Send a message to the SeeStar to go to a target.
    Args:
        ra (float): The right ascension of the target.
        dec (float): The declination of the target.
        target_name (str): The name of the target.
        exp_time (int): The exposure time in seconds.
    """
    global cmdid
    global logger
    # first we set the integration time of the sub exposures
    data = {}
    data['id'] = cmdid
    cmdid += 1
    data['method'] = 'set_setting'
    params = {}
    params['exp_ms'] = {}
    params['exp_ms']['stack_l']=int(exp_time)*1000
    params['exp_ms']['continous']=int(exp_cont)*1000
    data['params'] = params
    logger.debug(f'Exposure Settings: {data}')
    json_message2(data,logger)

    logger.debug("going to target...")
    data = {}
    data['id'] = cmdid
    cmdid += 1
    data['method'] = 'iscope_start_view'
    params = {}
    params['mode'] = 'star'
    ra_dec = [ra, dec]
    params['target_ra_dec'] = ra_dec
    params['target_name'] = target_name
    params['lp_filter'] = 1
    data['params'] = params
    json_message2(data,logger)
    
def start_stack():
    global cmdid
    global logger
    logger.debug("starting to stack...")
    data = {}
    data['id'] = cmdid
    cmdid += 1
    data['method'] = 'iscope_start_stack'
    params = {}
    params['restart'] = True
    data['params'] = params
    json_message2(data,logger)

def stop_stack():
    global cmdid
    global logger
    logger.debug("stop stacking...")
    data = {}
    data['id'] = cmdid
    cmdid += 1
    data['method'] = 'iscope_stop_view'
    params = {}
    params['stage'] = 'Stack'
    data['params'] = params
    json_message2(data,logger)

def wait_end_op():
    global op_state
    op_state = "working"
    heartbeat_timer = 0
    while op_state == "working":
        heartbeat_timer += 1
        if heartbeat_timer > 5:
            heartbeat_timer = 0
            json_message("test_connection")
        time.sleep(1)

    
def sleep_with_heartbeat():
    stacking_timer = 0
    while stacking_timer < session_time:         # stacking time per segment
        stacking_timer += 1
        if stacking_timer % 5 == 0:
            json_message("test_connection")
        time.sleep(1)

def parse_ra_to_float(ra_string):
    # Split the RA string into hours, minutes, and seconds
    hours, minutes, seconds = map(float, ra_string.split(':'))

    # Convert to decimal degrees
    ra_decimal = hours + minutes / 60 + seconds / 3600

    return ra_decimal
    
def parse_dec_to_float(dec_string):
    global logger
    # Split the Dec string into degrees, minutes, and seconds
    if dec_string[0] == '-':
        sign = -1
        dec_string = dec_string[1:]
    else:
        sign = 1
    #print(dec_string)
    degrees, minutes, seconds = map(float, dec_string.split(':'))

    # Convert to decimal degrees
    dec_decimal = sign * (degrees + minutes / 60 + seconds / 3600)

    return dec_decimal
    
is_watch_events = True
    
def main():
    global HOST
    global PORT
    global session_time
    global s
    global cmdid
    global is_watch_events
    global is_debug
    global op_state
    global exp_time
    global logger
    
    logger = CreateLogger()
    version_string = "1.0.0b1"
    logger.info(f"seestar_run version: {version_string}")

    parser = setup_argparse()
    args = parser.parse_args()
    HOST = sp.ip
    target_name = args.title
    center_RA = args.ra
    center_Dec = args.dec
    session_time = args.session_time
    exp_time = args.exp_time
    

    try:
        center_RA = float(center_RA)
    except ValueError:
        center_RA = parse_ra_to_float(center_RA)
        
    try:
        center_Dec = float(center_Dec)
    except ValueError:
        center_Dec = parse_dec_to_float(center_Dec)

    is_debug = args.is_debug
   
    PORT = sp.port
    cmdid = 999
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_result = s.connect_ex((HOST, PORT))
    if socket_result == 0:
        logger.debug("Connected to SeeStar")
    else:
        logger.error("Failed to connect to SeeStar")
        raise RuntimeError("Failed to connect to SeeStar")
    set_stack_settings(logger,cmdid) 
    with s:
        # flush the socket input stream for garbage
        get_socket_msg()
        
        if center_RA < 0:
            json_message("scope_get_equ_coord")
            data = get_socket_msg()
            parsed_data = json.loads(data)
            if parsed_data['method'] == "scope_get_equ_coord":
                data_result = parsed_data['result']
                center_RA = float(data_result['ra'])
                center_Dec = float(data_result['dec'])
                logger.debug(center_RA, center_Dec)
            
        # print input requests
        logger.info("received parameters:")
        logger.debug("  ip address    : " + HOST)
        logger.info("  target        : " + target_name)
        logger.debug("  RA            : ", center_RA)
        logger.debug("  Dec           : ", center_Dec)
        logger.debug("  session time  : ", session_time)
        logger.debug("  exp_time      : ", exp_time)        
         
        get_msg_thread = threading.Thread(target=receieve_message_thread_fn)
        get_msg_thread.start()
        
        mosaic_index = 0
        logger.info("Goto ", (center_RA, center_Dec))
        goto_target(center_RA, center_Dec, target_name)
        wait_end_op()
        logger.info("Goto operation finished")
        
        time.sleep(3)
        
        if op_state == "complete":
            start_stack()    
            sleep_with_heartbeat()
            stop_stack()
            logger.info("Stacking operation finished" + target_name)
        else:
            logger.error("Goto failed.") 
            raise RuntimeError("Goto failed.")      
        
    print("Finished seestar_run")
    is_watch_events = False
    get_msg_thread.join(timeout=10)
    s.close()
    if not is_debug:
        logger.info("Finished seestar_run") 
        #shutdown_seestar(logger,cmdid)
    
    
def setup_argparse():
    parser = argparse.ArgumentParser(description='Seestar Run')
    parser.add_argument('title', type=str, help="Observation Target Title")
    parser.add_argument('ra', type=str, help="Right Ascenscion Target")
    parser.add_argument('dec', type=str, help="Declination Target")
    parser.add_argument('exp_time', type=float, help="Time (in seconds) for images in the stack")
    parser.add_argument('session_time', type=float, help="Time (in seconds) for the stacking session")
    parser.add_argument('is_debug', type=str, default=False, nargs='?', help="Print debug logs while running.")
    return parser
    
if __name__ == "__main__":
    main()
    

 
