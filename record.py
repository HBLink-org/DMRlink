#!/usr/bin/env python
#
###############################################################################
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

# This is a sample application that "records" voice transmissions to
# a datafile... presumably to be played back later.

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import sys
import cPickle as pickle
from dmrlink import IPSC, NETWORK, networks, logger, int_id, hex_str_3

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


print('This program will record the first matching voice call and exit.\n')

while True:
    tx_type = raw_input('Group (g) or Private voice (p)? ')
    if tx_type == 'g' or tx_type == 'p':
        break
    print('...input must be either \'g\' or \'p\'')

while True:
    ts = raw_input('Which timeslot (1, 2 or \'both\')? ')
    if ts == '1' or ts == '2' or ts =='both':
        if ts == '1':
            ts = (0,)
        if ts == '2':
            ts = (1,)
        if ts == 'both':
            ts = (0,1)
        break
    print('...input must be \'1\', \'2\' or \'both\'')

id = raw_input('Which Group or Subscriber ID to record? ')
id = int(id)
id = hex_str_3(id)

filename = raw_input('Filename to use for this recording? ')

class recordIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    if tx_type == 'g':
	print('Initializing to record GROUP VOICE transmission')
        def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if id == _dst_sub and _ts in ts:
                if not _end:
                    if not self.CALL_DATA:
                        print('({}) Recording transmission from subscriber: {}' .format(_network, int_id(_src_sub)))
                    self.CALL_DATA.append(_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    print('({}) Transmission ended, writing to disk: {}' .format(_network, filename))
                    pickle.dump(self.CALL_DATA, open(filename, 'wb'))
                    reactor.stop()
                    print('Recording created, program terminating')
                
    if tx_type == 'p':
	print('Initializing ro record PRIVATE VOICE transmission')
        def private_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if id == _dst_sub and _ts in ts:
                if not _end:
                    if not self.CALL_DATA:
                        print('({}) Recording transmission from subscriber: {}' .format(_network, int_id(_src_sub)))
                    self.CALL_DATA.append(_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    print('({}) Transmission ended, writing to disk: {}' .format(_network, filename))
                    pickle.dump(self.CALL_DATA, open(filename, 'wb'))
                    reactor.stop()
                    print('Recording created, program terminating')

        
if __name__ == '__main__':
    logger.info('DMRlink \'record.py\' (c) 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = recordIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()
