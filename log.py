# Copyright (c) 2013 Cortney T. Buffington, N0MJS and the K0USY Group. n0mjs@me.com
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application that snoops voice traffic to log calls

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import time
from dmrlink import IPSC, UnauthIPSC, NETWORK, networks, get_info, int_id, subscriber_ids, peer_ids, talkgroup_ids, logger

class logIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.ACTIVE_CALLS = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************

    def call_mon_origin(self, _network, _data):
        print('({}) Repeater Call Monitor Origin Packet Received' .format(_network))
    
    def call_mon_rpt(self, _network, _data):
        print('({}) Repeater Call Monitor Repeating Packet Received' .format(_network))
    
    def call_mon_nack(self, _network, _data):
        print('({}) Repeater Call Monitor NACK Packet Received' .format(_network))
    
    def xcmp_xnl(self, _network, _data):
        print('({}) XCMP/XNL Packet Received From: {}' .format(_network, h(_data)))
    
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

class logUnauthIPSC(logIPSC):
    
    # There isn't a hash to build, so just return the data
    #
    def hashed_packet(self, _key, _data):
        return _data   
    
    # Remove the hash from a packet and return the payload... except don't
    #
    def strip_hash(self, _data):
        return _data
    
    # Everything is validated, so just return True
    #
    def validate_auth(self, _key, _data):
        return True
if __name__ == '__main__':
    logger.info('DMRlink \'log.py\' (c) 2013 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            if NETWORK[ipsc_network]['LOCAL']['AUTH_ENABLED']:
                networks[ipsc_network] = logIPSC(ipsc_network)
            else:
                networks[ipsc_network] = logUnauthIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network])
    reactor.run()