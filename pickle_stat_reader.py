from __future__ import print_function
from cPickle import load
from pprint import pprint
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h


# This is the only user-configuration necessary
#   Tell the program where the pickle file is
stat_file = '../dmrlink_stats.pickle'


def int_id(_hex_string):
    return int(h(_hex_string), 16)

def read_dict():
    try:
        with open(stat_file, 'rb') as file:
            NETWORK = load(file)
        return NETWORK
    except IOError as detail:
        print('I/O Error: {}'.format(detail))
    except EOFError:
        print('EOFError')

def print_stats():
    NETWORK = read_dict()
    if NETWORK != "None":
        print('NETWORK STATISTICS REPORT')
        for ipsc in NETWORK:
            stat = NETWORK[ipsc]['MASTER']['STATUS']
            print(ipsc)
            if (NETWORK[ipsc]['LOCAL']['MASTER_PEER']):
                print('  MASTER Information:')
                print('    This DMRLink IPSC Instance is the Master')
            else:
                print('  MASTER Information:')
                print('    RADIO ID: {} CONNECTED: {}, KEEP ALIVES: SENT {} RECEIVED {} MISSED {}'.format(str(int_id(NETWORK[ipsc]['MASTER']['RADIO_ID'])).rjust(8,'0'),stat['CONNECTED'],stat['KEEP_ALIVES_SENT'],stat['KEEP_ALIVES_RECEIVED'],stat['KEEP_ALIVES_MISSED']))
            print('  PEER Information:')
            for peer in NETWORK[ipsc]['PEERS']:
                stat = NETWORK[ipsc]['PEERS'][peer]['STATUS']
                if peer == NETWORK[ipsc]['LOCAL']['RADIO_ID']:
                    print('    RADIO ID: {} Is this instance'.format(str(int_id(peer)).rjust(8,'0')))
                else:
                    print('    RADIO ID: {} CONNECTED: {}, KEEP ALIVES: SENT {} RECEIVED {} MISSED {}'.format(str(int_id(peer)).rjust(8,'0'),stat['CONNECTED'],stat['KEEP_ALIVES_SENT'],stat['KEEP_ALIVES_RECEIVED'],stat['KEEP_ALIVES_MISSED']))
        print()
        print()

if __name__ == '__main__': 
    output_stats = task.LoopingCall(print_stats)
    output_stats.start(10)
    reactor.run()