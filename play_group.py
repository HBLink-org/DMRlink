#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application that "plays" a voice tranmission
# from a datafile... it is really proof of concept for now.

# PROOF OF CONCEPT ONLY - GUARANTEED TO NOT WORK AS IS!!!

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import sys, time
import cPickle as pickle
from dmrlink import IPSC, NETWORK, networks, logger, int_id, hex_str_3

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK; Dave K; and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__maintainer__ = 'Cort Buffington, N0MJS'
__version__ = '0.1a'
__email__ = 'n0mjs@me.com'
__status__ = 'pre-alpha'

# Constants for this application
#
BURST_DATA_TYPE = {
    'VOICE_HEAD':  '\x01',
    'VOICE_TERM':  '\x02',
    'SLOT1_VOICE': '\x0A',
    'SLOT2_VOICE': '\x8A'   
}

# path+filename for the transmission to play back
filename = '../test.pickle'

# groups that we want to trigger playback of this file (ts1 and ts2)
trigger_groups_1 = ['\x00\x00\x02', '\x00\x00\x03']
trigger_groups_2 = ['\x00\x00\x02', '\x00\x00\x03']

class playIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        self.event_id = 1
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def group_voice(self, _network, _src_sub, _dst_group, _ts, _end, _peerid, _data):
        if _end:
            if (_ts == 0 and _dst_group in trigger_groups_1) or (_ts == 1 and _dst_group in trigger_groups_2) :
                logger.info('(Event ID: %s) Playback triggered from TS %s, TGID %s', self.event_id, (_ts +1), int_id(_dst_group))
                
                # Determine the type of voice packet this is (see top of file for possible types)
                _burst_data_type = _data[30]
                if _ts == 0:
                    _TS = 'TS1'
                elif _ts == 1:
                    _TS = 'TS2'
                    
                time.sleep(2)
                self.CALL_DATA = pickle.load(open(filename, 'rb'))
                logger.info('(Event ID: %s) Playing back file: %s', self.event_id, filename)
                
                _self_peer = NETWORK[_network]['LOCAL']['RADIO_ID']
                _self_src = _self_peer[1:]
               
                for i in self.CALL_DATA:
                    _tmp_data = i
                    
                    # re-Write the peer radio ID to that of this program
                    _tmp_data = _tmp_data.replace(_peerid, _self_peer)
                    # re-Write the source subscriber ID to that of this program
                    _tmp_data = _tmp_data.replace(_src_sub, _self_src)
                    # Re-Write the destination Group ID
                    _tmp_data = _tmp_data.replace(_tmp_data[9:12], _dst_group)
                    
                    # Re-Write IPSC timeslot value
                    _call_info = int_id(_data[17:18])
                    if _ts == 0:
                        _call_info &= ~(1 << 5)
                    elif _ts == 1:
                        _call_info |= 1 << 5
                    _call_info = chr(_call_info)
                    _tmp_data = _tmp_data[:17] + _call_info + _tmp_data[18:]
                    
                    # Re-Write DMR timeslot value
                    # Determine if the slot is present, so we can translate if need be
                    '''
                    if _burst_data_type == BURST_DATA_TYPE['SLOT1_VOICE'] or _burst_data_type == BURST_DATA_TYPE['SLOT2_VOICE']:
                        # Re-Write timeslot if necessary...
                        if _ts == 0:
                            _burst_data_type = BURST_DATA_TYPE['SLOT1_VOICE']
                        elif _ts == 1:
                            _burst_data_type = BURST_DATA_TYPE['SLOT2_VOICE']
                        _tmp_data = _tmp_data[:30] + _burst_data_type + _tmp_data[31:]
                    '''
                    _tmp_data = self.hashed_packet(NETWORK[_network]['LOCAL']['AUTH_KEY'], _tmp_data)
                    # Send the packet to all peers in the target IPSC
                    self.send_to_ipsc(_tmp_data)
                    time.sleep(0.06)
                self.CALL_DATA = []
                logger.info('(Event ID: %s) Playback Completed', self.event_id)
                self.event_id = self.event_id + 1
        
if __name__ == '__main__':
    logger.info('DMRlink \'record.py\' (c) 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = playIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()
