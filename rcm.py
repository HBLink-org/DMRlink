#!/usr/bin/env python
#
# Copyright (c) 2013 Cortney T. Buffington, N0MJS and the K0USY Group. n0mjs@me.com
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application that uses the Repeater Call Monitor packets to display events in the IPSC
# NOTE: dmrlink.py MUST BE CONFIGURED TO CONNECT AS A "REPEATER CALL MONITOR" PEER!!!
# ALSO NOTE, I'M NOT DONE MAKING THIS WORK, SO UNTIL THIS MESSAGE IS GONE, DON'T EXPECT GREAT THINGS.

from __future__ import print_function
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h

import time
import binascii
import dmrlink
from dmrlink import IPSC, NETWORK, networks, get_info, int_id, subscriber_ids, peer_ids, talkgroup_ids, logger

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2013 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK, Dave K, and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__version__ = '0.2a'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'Production'

# Constants

TS = {
    '\x00': '1',
    '\x01': '2'
}

NACK = {
    '\x05': 'BSID Start',
    '\x06': 'BSID End'
}

TYPE = {
    '\x30': 'Private Data Set-Up',
    '\x31': 'Group Data Set-Up',
    '\x32': 'Private CSBK Set-Up',
    '\x47': 'Radio Check Request',
    '\x45': 'Call Alert',
    '\x4D': 'Remote Monitor Request',
    '\x4F': 'Group Voice',
    '\x50': 'Private Voice',
    '\x51': 'Group Data',
    '\x52': 'Private Data',
    '\x53': 'All Call'
}

SEC = {
    '\x00': 'None',
    '\x01': 'Basic',
    '\x02': 'Enhanced'
}

STATUS = {
    '\x01': 'Active',
    '\x02': 'End',
    '\x05': 'TS In Use',
    '\x0A': 'BSID ON',
    '\x0B': 'Timeout',
    '\x0C': 'TX Interrupt'
}


class rcmIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************

    def call_mon_origin(self, _network, _data):
        _source = _data[1:5]
        _ipsc_src = _data[5:9]
        _rf_src = _data[16:19]
        _rf_tgt = _data[19:22]
        
        _ts = _data[13]
        _status = _data[15]
        _type = _data[22]
        _sec = _data[24]
        
        _ipsc_src = get_info(int_id(_ipsc_src), peer_ids)
        _rf_src = get_info(int_id(_rf_src), subscriber_ids)
        
        if _type == '\x4F' or '\x51':
            _rf_tgt = get_info(int_id(_rf_tgt), talkgroup_ids)
        else:
            _rf_tgt = get_info(int_id(_rf_tgt), subscriber_ids)
        
        print('IPSC:        ', _network)
        print('IPSC Source: ', _ipsc_src)
        print('Timeslot:    ', TS[_ts])
        print('Status:      ', STATUS[_status])
        print('Type:        ', TYPE[_type])
        print('Source Sub:  ', _rf_src)
        print('Target Sub:  ', _rf_tgt)
        print()
    
    def call_mon_rpt(self, _network, _data):
        #print('({}) Repeater Call Monitor Repeating Packet: {}' .format(_network, h(_data)))
        pass
        
    def call_mon_nack(self, _network, _data):
        #print('({}) Repeater Call Monitor NACK Packet: {}' .format(_network, h(_data)))
        pass
        
    def xcmp_xnl(self, _network, _data):
        #print('({}) XCMP/XNL Packet Received From: {}' .format(_network, h(_data)))
        pass
    
    def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        pass
        
    def private_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        pass
        
    def group_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        pass
    
    def private_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        pass
        
    def repeater_wake_up(self, _network, _data):
        _source = _data[1:5]
        _source_dec = int_id(_source)
        _source_name = get_info(_source_dec, peer_ids)
        print('({}) Repeater Wake-Up Packet Received: {} ({})' .format(_network, _source_name, _source_dec))


if __name__ == '__main__':
    logger.info('DMRlink \'rcm.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = rcmIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network])
    reactor.run()