from __future__ import print_function
from cPickle import load
from pprint import pprint
from os.path import getmtime
from time import sleep


# This is the only user-configuration necessary
#   Tell the program where the pickle file is
stat_file = 'dmrlink_stats.pickle'


last = getmtime(stat_file)


def read_dict():
    try:
        with open(stat_file, 'rb') as file:
            NETWORK = load(file)
        return NETWORK
    except IOError as detail:
        print('I/O Error: {}'.format(detail))
    except EOFError:
        print('EOFError')


pprint(read_dict())

while 1:
    sleep(1)
    now = getmtime(stat_file)
    if now > last:
        last = now
        pprint(read_dict())