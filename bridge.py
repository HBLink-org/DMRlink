#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application to bridge traffic between IPSC networks

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import sys
from dmrlink import IPSC, NETWORK, networks, send_to_ipsc, dmr_nat, logger

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK, Dave K, and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__version__ = '0.2a'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'Production'

NAT = 0
#NAT = '\x2f\x9b\x80'

# Notes and pieces of next steps...
# RPT_WAKE_UP = b'\x85' + NETWORK[_network]['LOCAL']['RADIO_ID] + b'\x00\x00\x00\x01' + b'\x01' + b'\x01'
# TS1 = 0, TS2 = 1

# Import Bridging rules
#
try:
    from bridge_rules import RULES
except ImportError:
    sys.exit('Bridging rules file not found or invalid')


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
            # Matching for rules is against the Destination Group in the SOURCE packet (SRC_GROUP)
            if rule['SRC_GROUP'] == _dst_group and rule['SRC_TS'] == _ts:
                _tmp_data = _data
                _target = rule['DST_NET']
                # Re-Write the IPSC SRC to match the target network's ID
                _tmp_data = _tmp_data.replace(_peerid, NETWORK[_target]['LOCAL']['RADIO_ID'])
                # Re-Write the destination Group ID
                _tmp_data = _tmp_data.replace(_dst_group, rule['DST_GROUP'])
                
                # NAT doesn't work well... use at your own risk!
                if NAT:
                    _tmp_data = dmr_nat(_tmp_data, _src_sub, NAT)
                
                # Calculate and append the authentication hash for the target network... if necessary
                if NETWORK[_target]['LOCAL']['AUTH_ENABLED']:
                    _tmp_data = self.hashed_packet(NETWORK[_target]['LOCAL']['AUTH_KEY'], _tmp_data)
                # Send the packet to all peers in the target IPSC
                send_to_ipsc(_target, _tmp_data)

if __name__ == '__main__':
    logger.info('DMRlink \'bridge.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = bridgeIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network])
    reactor.run()
