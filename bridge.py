#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application to bridge traffic between IPSC networks. it uses
# one required (bridge_rules.py) and one optional (known_bridges.py) additional
# configuration files. Both files have their own documentation for use.
#
# "bridge_rules" contains the IPSC network, Timeslot and TGID matching rules to
# determine which voice calls are bridged between IPSC networks and which are
# not.
#
# "known_bridges" contains DMR radio ID numbers of known bridges. This file is
# used when you want bridge.py to be "polite" or serve as a backup bridge. If
# a known bridge exists in either a source OR target IPSC network, then no
# bridging between those IPSC networks will take place. This behavior is
# dynamic and updates each keep-alive interval (main configuration file).
# For faster failover, configure a short keep-alive time and a low number of
# missed keep-alives before timout. I recommend 5 sec keep-alive and 3 missed.
# That gives a worst-case scenario of 15 seconds to fail over. Recovery will
# typically happen with a single "blip" in the transmission up to about 5
# seconds.
#
# While this file is listed as Beta status, K0USY Group depends on this code
# for the bridigng of it's many repeaters. We consider it reliable, but you
# get what you pay for... as usual, no guarantees.

from __future__ import print_function
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h

import sys
from dmrlink import IPSC, NETWORK, networks, dmr_nat, logger, hex_str_3, hex_str_4, int_id

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK, Dave K, and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__version__ = '0.27b'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'beta'


BURST_DATA_TYPE = {
    'VOICE_HEAD':  '\x01',
    'VOICE_TERM':  '\x02',
    'SLOT1_VOICE': '\x0A',
    'SLOT2_VOICE': '\x8A'   
}

# Notes and pieces of next steps...
# RPT_WAKE_UP = b'\x85' + NETWORK[_network]['LOCAL']['RADIO_ID] + b'\x00\x00\x00\x01' + b'\x01' + b'\x01'
# TS1 = 0, TS2 = 1

# Import Bridging rules
# Note: A stanza *must* exist for any IPSC configured in the main
# configuration file and listed as "active". It can be empty, 
# but it has to exist.
#
try:
    from bridge_rules import RULES
    logger.info('Bridge rules file found and rules imported')
except ImportError:
    sys.exit('Bridging rules file not found or invalid')

# Convert integer GROUP ID numbers from the config into hex strings
# we need to send in the actual data packets.
#

for _ipsc in RULES:
    for _rule in RULES[_ipsc]['GROUP_VOICE']:
        _rule['SRC_GROUP'] = hex_str_3(_rule['SRC_GROUP'])
        _rule['DST_GROUP'] = hex_str_3(_rule['DST_GROUP'])
        _rule['SRC_TS'] = _rule['SRC_TS'] - 1
        _rule['DST_TS'] = _rule['DST_TS'] - 1


# Import List of Bridges
# This is how we identify known bridges. If one of these is present
# and it's mode byte is set to bridge, we don't
#
try:
    from known_bridges import BRIDGES
    logger.info('Known bridges file found and bridge ID list imported ')
except ImportError:
    logger.critical('\'known_bridges.py\' not found - backup bridge service will not be enabled')
    BRIDGES = []


# The class methods we override, including __init__ will be different
# depending on whether or not there is a known_bridges.py file, and
# hence whether or not we will implement backup/polite bridging or
# not (standard bridging). So, we test to see if the known bridges
# data structure "BRIDGES" was imported and had entries or not. If
# it did not import or did not have any entries, standard bridging
# is used.
#
if BRIDGES:
    logger.info('Initializing class methods for backup/polite bridging')
    class bridgeIPSC(IPSC):
      
        def __init__(self, *args, **kwargs):
            IPSC.__init__(self, *args, **kwargs)
            self.BRIDGE = False
            self.ACTIVE_CALLS = []
            logger.info('(%s) Initializing bridge status as: %s', self._network, self.BRIDGE)
    
        # Setup the backup/polite bridging maintenance loop (based on keep-alive timer)
        def startProtocol(self):
            IPSC.startProtocol(self)
        
            self._bridge_presence = task.LoopingCall(self.bridge_presence_loop)
            self._bridge_presence_loop = self._bridge_presence.start(self._local['ALIVE_TIMER'])
    
        # This is the backup/polite bridge maintenance loop
        def bridge_presence_loop(self):
            _temp_bridge = True
            for peer in BRIDGES:
                _peer = hex_str_4(peer)
            
                if _peer in self._peers.keys() and (self._peers[_peer]['MODE_DECODE']['TS_1'] or self._peers[_peer]['MODE_DECODE']['TS_2']):
                    _temp_bridge = False
                    logger.debug('(%s) Peer %s is an active bridge', self._network, int_id(_peer))
            
                if _peer == self._master['RADIO_ID'] \
                    and self._master['STATUS']['CONNECTED'] \
                    and (self._master['MODE_DECODE']['TS_1'] or self._master['MODE_DECODE']['TS_2']):
                    _temp_bridge = False
                    logger.debug('(%s) Master %s is an active bridge',self._network, int_id(_peer))
            
            if self.BRIDGE != _temp_bridge:
                logger.info('(%s) Changing bridge status to: %s', self._network, _temp_bridge )
            self.BRIDGE = _temp_bridge
        
            

        #************************************************
        #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
        #************************************************
        #
        def group_voice(self, _network, _src_sub, _dst_group, _ts, _end, _peerid, _data):
            logger.debug('(%s) Group Voice Packet Received From: %s, IPSC Peer %s, Destination %s', _network, int_id(_src_sub), int_id(_peerid), int_id(_dst_group))
            if _ts not in self.ACTIVE_CALLS:
                self.ACTIVE_CALLS.append(_ts)
                # send repeater wake up, but send them when a repeater is likely not TXing check time since end (see below)
            if _end:
                self.ACTIVE_CALLS.remove(_ts)
                # flag the time here so we can test to see if the last call ended long enough ago to send a wake-up
                # timer = time()
            
            for rule in RULES[_network]['GROUP_VOICE']:
                _target = rule['DST_NET']
                # Matching for rules is against the Destination Group in the SOURCE packet (SRC_GROUP)
                if rule['SRC_GROUP'] == _dst_group and rule['SRC_TS'] == _ts and (self.BRIDGE == True or networks[_target].BRIDGE == True):
                    _tmp_data = _data
                    # Re-Write the IPSC SRC to match the target network's ID
                    _tmp_data = _tmp_data.replace(_peerid, NETWORK[_target]['LOCAL']['RADIO_ID'])
                    # Re-Write the destination Group ID
                    _tmp_data = _tmp_data.replace(_dst_group, rule['DST_GROUP'])
                    
                    # Re-Write IPSC timeslot value
                    _call_info = int_id(_data[17:18])
                    if rule['DST_TS'] == 0:
                        _call_info &= ~(1 << 5)
                    elif rule['DST_TS'] == 1:
                        _call_info |= 1 << 5
                    _call_info = chr(_call_info)
                    _tmp_data = _tmp_data[:17] + _call_info + _tmp_data[18:] 
                    
                    # Re-Write DMR timeslot value
                    # Determine if the slot is present, so we can translate if need be
                    _burst_data_type = _data[30]
                    if _burst_data_type == BURST_DATA_TYPE['SLOT1_VOICE'] or _burst_data_type == BURST_DATA_TYPE['SLOT2_VOICE']:
                        _slot_valid = True
                    else:
                        _slot_valid = False
                    # Re-Write timeslot if necessary...
                    if _slot_valid:
                        if rule['DST_TS'] == 0:
                            _burst_data_type = BURST_DATA_TYPE['SLOT1_VOICE']
                        elif rule['DST_TS'] == 1:
                            _burst_data_type = BURST_DATA_TYPE['SLOT2_VOICE']
                        _tmp_data = _tmp_data[:30] + _burst_data_type + _tmp_data[31:]
                
                    # Calculate and append the authentication hash for the target network... if necessary
                    if NETWORK[_target]['LOCAL']['AUTH_ENABLED']:
                        _tmp_data = self.hashed_packet(NETWORK[_target]['LOCAL']['AUTH_KEY'], _tmp_data)
                    # Send the packet to all peers in the target IPSC
                    networks[_target].send_to_ipsc(_tmp_data)

else:
    logger.info('Initializing class methods for standard bridging')
    class bridgeIPSC(IPSC):
      
        def __init__(self, *args, **kwargs):
            IPSC.__init__(self, *args, **kwargs)
            self.ACTIVE_CALLS = []
        
        
        #************************************************
        #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
        #************************************************
        #
        def group_voice(self, _network, _src_sub, _dst_group, _ts, _end, _peerid, _data):
            if _ts not in self.ACTIVE_CALLS:
                self.ACTIVE_CALLS.append(_ts)
                # send repeater wake up, but send them when a repeater is likely not TXing check time since end (see below)
            if _end:
                self.ACTIVE_CALLS.remove(_ts)
                # flag the time here so we can test to see if the last call ended long enough ago to send a wake-up
                # timer = time()
            
            for rule in RULES[_network]['GROUP_VOICE']:
                _target = rule['DST_NET']
                # Matching for rules is against the Destination Group in the SOURCE packet (SRC_GROUP)
                if rule['SRC_GROUP'] == _dst_group and rule['SRC_TS'] == _ts:
                    _tmp_data = _data
                    # Re-Write the IPSC SRC to match the target network's ID
                    _tmp_data = _tmp_data.replace(_peerid, NETWORK[_target]['LOCAL']['RADIO_ID'])
                    # Re-Write the destination Group ID
                    _tmp_data = _tmp_data.replace(_dst_group, rule['DST_GROUP'])
                
                    # Re-Write IPSC timeslot value
                    _call_info = int_id(_data[17:18])
                    if rule['DST_TS'] == 0:
                        _call_info &= ~(1 << 5)
                    elif rule['DST_TS'] == 1:
                        _call_info |= 1 << 5
                    _call_info = chr(_call_info)
                    _tmp_data = _tmp_data[:17] + _call_info + _tmp_data[18:] 
                    
                    # Re-Write DMR timeslot value
                    # Determine if the slot is present, so we can translate if need be
                    _burst_data_type = _data[30]
                    if _burst_data_type == BURST_DATA_TYPE['SLOT1_VOICE'] or _burst_data_type == BURST_DATA_TYPE['SLOT2_VOICE']:
                        _slot_valid = True
                    else:
                        _slot_valid = False
                    # Re-Write timeslot if necessary...
                    if _slot_valid:
                        if rule['DST_TS'] == 0:
                            _burst_data_type = BURST_DATA_TYPE['SLOT1_VOICE']
                        elif rule['DST_TS'] == 1:
                            _burst_data_type = BURST_DATA_TYPE['SLOT2_VOICE']
                        _tmp_data = _tmp_data[:30] + _burst_data_type + _tmp_data[31:]
                
                    # Calculate and append the authentication hash for the target network... if necessary
                    if NETWORK[_target]['LOCAL']['AUTH_ENABLED']:
                        _tmp_data = self.hashed_packet(NETWORK[_target]['LOCAL']['AUTH_KEY'], _tmp_data)
                    # Send the packet to all peers in the target IPSC
                    networks[_target].send_to_ipsc(_tmp_data)

                
                

if __name__ == '__main__':
    logger.info('DMRlink \'bridge.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = bridgeIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()