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

# This is a sample application that snoops voice traffic to log calls

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import time
from dmrlink import IPSC, NETWORK, networks, get_info, int_id, subscriber_ids, peer_ids, talkgroup_ids, logger

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK, Dave Kierzkowski, KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


class logIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.ACTIVE_CALLS = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    
    def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
    #    _log = logger.debug
        if (_ts not in self.ACTIVE_CALLS) or _end:
            _time       = time.strftime('%m/%d/%y %H:%M:%S')
            _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
            _peerid     = get_info(int_id(_peerid), peer_ids)
            _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
            if not _end:    self.ACTIVE_CALLS.append(_ts)
            if _end:        self.ACTIVE_CALLS.remove(_ts)
        
            if _ts:     _ts = 2
            else:       _ts = 1
            if _end:    _end = 'END'
            else:       _end = 'START'
        
            print('{} ({}) Call {} Group Voice: \n\tIPSC Source:\t{}\n\tSubscriber:\t{}\n\tDestination:\t{}\n\tTimeslot\t{}' .format(_time, _network, _end, _peerid, _src_sub, _dst_sub, _ts))

    def private_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
    #    _log = logger.debug    
        if (_ts not in self.ACTIVE_CALLS) or _end:
            _time       = time.strftime('%m/%d/%y %H:%M:%S')
            _dst_sub    = get_info(int_id(_dst_sub), subscriber_ids)
            _peerid     = get_info(int_id(_peerid), peer_ids)
            _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
            if not _end:    self.ACTIVE_CALLS.append(_ts)
            if _end:        self.ACTIVE_CALLS.remove(_ts)
        
            if _ts:     _ts = 2
            else:       _ts = 1
            if _end:    _end = 'END'
            else:       _end = 'START'
        
            print('{} ({}) Call {} Private Voice: \n\tIPSC Source:\t{}\n\tSubscriber:\t{}\n\tDestination:\t{}\n\tTimeslot\t{}' .format(_time, _network, _end, _peerid, _src_sub, _dst_sub, _ts))
    
    def group_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
        _peerid     = get_info(int_id(_peerid), peer_ids)
        _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
        print('({}) Group Data Packet Received From: {}' .format(_network, _src_sub))
    
    def private_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        _dst_sub    = get_info(int_id(_dst_sub), subscriber_ids)
        _peerid     = get_info(int_id(_peerid), peer_ids)
        _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
        print('({}) Private Data Packet Received From: {} To: {}' .format(_network, _src_sub, _dst_sub))


if __name__ == '__main__':
    logger.info('DMRlink \'log.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = logIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()