import logging
import sys

def CreateLogger():
    # Create a custom logger 
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler('seestar_varstar.log')

    # Set levels for handlers
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters and add them to handlers
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return(logger)

def json_message2(data):
    if data:
        json_data = json.dumps(data)
        if is_debug:
            logger.debug("Sending2 %s" % json_data)
        resp = send_message(json_data + "\r\n")
        if is_debug:
            logger.debug("Response2: %s" % resp)
        return resp
    else:
        return None


def shutdown_seestar():
    """
    Shutdown the seestar device
    """
    global cmdid
    data = {}
    data['id'] = cmdid
    cmdid+=1
    data['method'] = 'pi_shutdown'
    json_message2(data)


def set_stack_settings():
    global cmdid
    logger.debug("set stack setting to record individual frames")
    data = {}
    data['id'] = cmdid
    cmdid += 1
    data['method'] = 'set_stack_setting'
    params = {}
    params['save_discrete_frame'] = True
    data['params'] = params
    return(json_message2(data))
