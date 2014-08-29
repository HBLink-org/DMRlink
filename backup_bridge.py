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
from twisted.internet import task
from binascii import b2a_hex as h

import sys
from dmrlink import IPSC, NETWORK, networks, send_to_ipsc, dmr_nat, logger, hex_str_4, int_id

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK, Dave K, and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__version__ = '0.1b'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'Beta'


# Import Bridging rules
# Note: A stanza *must* exist for any IPSC configured in the main
# configuration file. It can be empty, but it has to exist.
#
try:
    from bridge_rules import RULES
    logger.info('Bridge rules file found and rules imported')
except ImportError:
    sys.exit('Bridging rules file not found or invalid')

# Import List of Bridges
# This is how we identify known bridges. If one of these is present
# and it's mode byte is set to bridge, we don't
#
try:
    from known_bridges import BRIDGES
    logger.info('Known bridges file found and bridge ID list imported ')
except ImportError:
    logger.critical('(backup_bridge.py) NO BRIDGES FILE FOUND, INITIALIZING NULL')
    BRIDGES = []


class bridgeIPSC(IPSC):
      
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.BRIDGE = False
        self.ACTIVE_CALLS = []
        logger.info('(%s) Initializing bridge status as: %s', self._network, self.BRIDGE)
    
    def startProtocol(self):
        IPSC.startProtocol(self)
        
        self._bridge_presence = task.LoopingCall(self.bridge_presence_loop)
        self._bridge_presence_loop = self._bridge_presence.start(self._local['ALIVE_TIMER'])
    
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