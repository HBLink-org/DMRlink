#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application that "records" voice transmissions to
# a datafile... presumably to be played back later.

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import sys
from dmrlink import IPSC, NETWORK, networks, logger, int_id, hex_str_3

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK; Dave K; and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'pre-alpha'


print('This program will record the first matching voice call and exit.\n')

while True:
    _my_tx_type = raw_input('Group (g) or Private voice (p)? ')
    if _my_tx_type == 'g' or _my_tx_type == 'p':
        break
    print('...input must be either \'g\' or \'p\'')

while True:
    _my_ts = raw_input('Which timeslot (1, 2 or \'both\')? ')
    if _my_ts == '1' or _my_ts == '2' or _my_ts =='both':
        if _my_ts == '1':
            _my_ts = (0,)
        if _my_ts == '2':
            _my_ts = (1,)
        if _my_ts == 'both':
            _my_ts = (0,1)
        break
    print('...input must be \'1\', \'2\' or \'both\'')

_my_id = raw_input('Which Group or Subscriber ID to record? ')
_my_id = int(_my_id)
_my_id = hex_str_3(_my_id)

_my_filename = raw_input('Filename to use for this recording? ')

record_file = open(_my_filename, 'w')

class recordIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    if _my_tx_type == 'g':
	print('Initializing to record GROUP VOICE transmission')
        def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if _my_id == _dst_sub and _ts in _my_ts:
                if not _end:
                    if not self.CALL_DATA:
                        print('({}) Recording transmission from subscriber: {}' .format(_network, int_id(_src_sub)))
                    self.CALL_DATA.append(_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    print('({}) Transmission ended, writing to disk: {}' .format(_network, _my_filename))
                    for i in self.CALL_DATA:
                        record_file.write(i)
                    record_file.close                       
                    reactor.stop()
                    print('Recording created, program terminating')
                
    if _my_tx_type == 'p':
	print('Initializing ro record PRIVATE VOICE transmission')
        def private_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if _my_id == _dst_sub and _ts in _my_ts:
                if not _end:
                    if not self.CALL_DATA:
                        print('({}) Recording transmission from subscriber: {}' .format(_network, int_id(_src_sub)))
                    self.CALL_DATA.append(_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    print('({}) Transmission ended, writing to disk: {}' .format(_network, _my_filename))
                    for i in self.CALL_DATA:
                        record_file.write(i)
                    record_file.close
                    reactor.stop()
                    print('Recording created, program terminating')

        
if __name__ == '__main__':
    logger.info('DMRlink \'record.py\' (c) 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = recordIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network])
    reactor.run()
