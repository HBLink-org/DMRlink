#!/usr/bin/env python
#
###############################################################################
# hb_router.py -- a call routing applicaiton for hblink.py
#   Copyright (C) 2016  Cortney T. Buffington, N0MJS <n0mjs@me.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
###############################################################################

from __future__ import print_function
from cPickle import load
from pprint import pprint
from time import ctime
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2015 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK, Dave Kierzkowski, KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


# This is the only user-configuration necessary
#   Tell the program where the pickle file is
#   Tell the program how often to print a report
stat_file = '../dmrlink_stats.pickle'
frequency = 30


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
        print('NETWORK STATISTICS REPORT:', ctime())

        for ipsc in NETWORK:
            stat = NETWORK[ipsc]['MASTER']['STATUS']
            master = NETWORK[ipsc]['LOCAL']['MASTER_PEER']
            
            print(ipsc)
            
            if master:
                print('  MASTER Information:')
                print('    RADIO ID: {} (self)'.format(str(int_id(NETWORK[ipsc]['LOCAL']['RADIO_ID'])).rjust(8,'0')))
            else:
                print('  MASTER Information:')
                print('    RADIO ID: {} CONNECTED: {}, KEEP ALIVES: SENT {} RECEIVED {} MISSED {} ({})'.format(\
                        str(int_id(NETWORK[ipsc]['MASTER']['RADIO_ID'])).rjust(8,'0'),\
                        stat['CONNECTED'],stat['KEEP_ALIVES_SENT'],\
                        stat['KEEP_ALIVES_RECEIVED'],\
                        stat['KEEP_ALIVES_MISSED'],\
                        NETWORK[ipsc]['MASTER']['IP']))
                        
                        
            print('  PEER Information:')
            
            if master:
                for peer in NETWORK[ipsc]['PEERS']:
                    stat = NETWORK[ipsc]['PEERS'][peer]['STATUS']
                    print('    RADIO ID: {} CONNECTED: {}, KEEP ALIVES: RECEIVED {} ({})'.format(\
                        str(int_id(peer)).rjust(8,'0'),\
                        stat['CONNECTED'],\
                        stat['KEEP_ALIVES_RECEIVED'],\
                        NETWORK[ipsc]['PEERS'][peer]['IP']))
            else:
                for peer in NETWORK[ipsc]['PEERS']:
                    stat = NETWORK[ipsc]['PEERS'][peer]['STATUS']
                    if peer == NETWORK[ipsc]['LOCAL']['RADIO_ID']:
                        print('    RADIO ID: {} (self)'.format(str(int_id(peer)).rjust(8,'0')))
                    else:
                        print('    RADIO ID: {} CONNECTED: {}, KEEP ALIVES: SENT {} RECEIVED {} MISSED {} ({})'.format(\
                            str(int_id(peer)).rjust(8,'0'),\
                            stat['CONNECTED'],\
                            stat['KEEP_ALIVES_SENT'],\
                            stat['KEEP_ALIVES_RECEIVED'],\
                            stat['KEEP_ALIVES_MISSED'],\
                            NETWORK[ipsc]['PEERS'][peer]['IP']))
        print()
        print()

if __name__ == '__main__': 
    output_stats = task.LoopingCall(print_stats)
    output_stats.start(frequency)
    reactor.run()