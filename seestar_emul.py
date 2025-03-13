"""The module provides a class to emulate the SEESTAR_run module for testing purposes.
The class has a method that emulates the seestar_run_runner method of the SEESTAR_run module.
The method takes the same arguments as the seestar_run_runner method and prints the arguments
to the console. The method returns 0 if the arguments are valid and 1 if the arguments are invalid.
The class can be used to test the seestar_run_runner method without running the SEESTAR_run module.
"""
import random

def seestar_run_runner(targetName, coords, exptime, totaltime):
    """Emulate the seestar_run_runner method of the SEESTAR_run module.
    Args:
    targetName (str): The name of the target.
    coords (list): The coordinates of the target.
    exptime (int or float): The exposure time in seconds.
    Returns:
    int: 0 if the arguments are valid, 1 if the arguments are invalid
    """
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
    # Print the arguments to the console
    print(targetName, coords, exptime, totaltime)
    # every now and then the seestar_run_runner method will return 1
    # to simulate an instrument error - this ins generated at random a certain fraction of the time e_frac
    e_frac = 0.1
    if random.random() < e_frac:
        raise Exception('Instrument error')
    return 0

if __name__ == '__main__':
    # Test the seestar_run_runner method
    # read arguments from the command line
    import sys
    targetName = sys.argv[1]
    coords = [float(sys.argv[2]), float(sys.argv[3])]
    exptime = float(sys.argv[4])
    totaltime = float(sys.argv[5])
    # call the seestar_run_runner method
    seestar_run_runner(targetName, coords, exptime, totaltime)
    # return 0 to indicate success
    sys.exit(0)
