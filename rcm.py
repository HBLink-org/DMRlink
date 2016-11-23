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

# This is a sample application that uses the Repeater Call Monitor packets to display events in the IPSC
# NOTE: dmrlink.py MUST BE CONFIGURED TO CONNECT AS A "REPEATER CALL MONITOR" PEER!!!
# ALSO NOTE, I'M NOT DONE MAKING THIS WORK, SO UNTIL THIS MESSAGE IS GONE, DON'T EXPECT GREAT THINGS.

from __future__ import print_function
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h

import datetime
import binascii
import dmrlink
from dmrlink import IPSC, NETWORK, networks, get_info, int_id, subscriber_ids, peer_ids, talkgroup_ids, logger

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


try:
    from ipsc.ipsc_message_types import *
except ImportError:
    sys.exit('IPSC message types file not found or invalid')

status = True
rpt = True
nack = True

class rcmIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def call_mon_status(self, _network, _data):
        if not status:
            return
        _source =   _data[1:5]
        _ipsc_src = _data[5:9]
        _seq_num =  _data[9:13]
        _ts =       _data[13]
        _status =   _data[15] # suspect [14:16] but nothing in leading byte?
        _rf_src =   _data[16:19]
        _rf_tgt =   _data[19:22]
        _type =     _data[22]
        _prio =     _data[23]
        _sec =      _data[24]
        
        _source = str(int_id(_source)) + ', ' + str(get_info(int_id(_source), peer_ids))
        _ipsc_src = str(int_id(_ipsc_src)) + ', ' + str(get_info(int_id(_ipsc_src), peer_ids))
        _rf_src = str(int_id(_rf_src)) + ', ' + str(get_info(int_id(_rf_src), subscriber_ids))
        
        if _type == '\x4F' or '\x51':
            _rf_tgt = 'TGID: ' + str(int_id(_rf_tgt)) + ', ' + str(get_info(int_id(_rf_tgt), talkgroup_ids))
        else:
            _rf_tgt = 'SID: ' + str(int_id(_rf_tgt)) + ', ' + str(get_info(int_id(_rf_tgt), subscriber_ids))
        
        print('Call Monitor - Call Status')
        print('TIME:        ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print('DATA SOURCE: ', _source)
        print('IPSC:        ', _network)
        print('IPSC Source: ', _ipsc_src)
        print('Timeslot:    ', TS[_ts])
        try:
            print('Status:      ', STATUS[_status])
        except KeyError:
            print('Status (unknown): ', h(_status))
        try:
            print('Type:        ', TYPE[_type])
        except KeyError:
            print('Type (unknown): ', h(_type))
        print('Source Sub:  ', _rf_src)
        print('Target Sub:  ', _rf_tgt)
        print()
    
    def call_mon_rpt(self, _network, _data):
        if not rpt:
            return
        _source    = _data[1:5]
        _ts1_state = _data[5]
        _ts2_state = _data[6]
        
        _source = str(int_id(_source)) + ', ' + str(get_info(int_id(_source), peer_ids))
        
        print('Call Monitor - Repeater State')
        print('TIME:         ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print('DATA SOURCE:  ', _source)
     
        try:
            print('TS1 State:    ', REPEAT[_ts1_state])
        except KeyError:
            print('TS1 State (unknown): ', h(_ts1_state))
        try:
            print('TS2 State:    ', REPEAT[_ts2_state])
        except KeyError:
            print('TS2 State (unknown): ', h(_ts2_state))
        print()
            
    def call_mon_nack(self, _network, _data):
        if not nack:
            return
        _source = _data[1:5]
        _nack =   _data[5]
        
        _source = get_info(int_id(_source), peer_ids)
        
        print('Call Monitor - Transmission NACK')
        print('TIME:        ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print('DATA SOURCE: ', _source)
        try:
            print('NACK Cause:  ', NACK[_nack])
        except KeyError:
            print('NACK Cause (unknown): ', h(_nack))
        print()
    
    def repeater_wake_up(self, _network, _data):
        _source = _data[1:5]
        _source_dec = int_id(_source)
        _source_name = get_info(_source_dec, peer_ids)
        #print('({}) Repeater Wake-Up Packet Received: {} ({})' .format(_network, _source_name, _source_dec))


if __name__ == '__main__':
    logger.info('DMRlink \'rcm.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = rcmIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()