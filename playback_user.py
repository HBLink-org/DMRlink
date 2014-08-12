#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application that "records" and replays transmissions for testing.

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import sys, time
from dmrlink import IPSC, NETWORK, networks, logger, dmr_nat, int_id, send_to_ipsc, hex_str_3

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK; Dave K; and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__version__ = '0.1b'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'pre-alpha'


try:
    from playback_user_config import *
except ImportError:
    sys.exit('Configuration file not found or invalid')

HEX_SUB = hex_str_3(SUB)
BOGUS_SUB = '\xFF\xFF\xFF'

class playbackIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def private_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
    #def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        if HEX_SUB == _dst_sub and TS == _ts:
            if not _end:
                if not self.CALL_DATA:
                    logger.info('(%s) Receiving transmission to be played back from subscriber: %s, to subscriber: %s', _network, int_id(_src_sub), int_id(_dst_sub))
                _tmp_data = _data
                #_tmp_data = dmr_nat(_data, _src_sub, NETWORK[_network]['LOCAL']['RADIO_ID'])
                self.CALL_DATA.append(_tmp_data)
            if _end:
                self.CALL_DATA.append(_data)
                time.sleep(1)
                logger.info('(%s) Playing back transmission from subscriber: %s, to subscriber %s', _network, int_id(_src_sub), int_id(_dst_sub))
                _orig_src = _src_sub
                _orig_dst = _dst_sub
                for i in self.CALL_DATA:
                    _tmp_data = i
                    #print(h(_tmp_data))
                    _tmp_data = _tmp_data.replace(_peerid, NETWORK[_network]['LOCAL']['RADIO_ID'])
                    _tmp_data = _tmp_data.replace(_dst_sub, BOGUS_SUB)
                    _tmp_data = _tmp_data.replace(_src_sub, _orig_dst)
                    _tmp_data = _tmp_data.replace(BOGUS_SUB, _orig_src)
                    _tmp_data = self.hashed_packet(NETWORK[_network]['LOCAL']['AUTH_KEY'], _tmp_data)
                    # Send the packet to all peers in the target IPSC
                    #print(h(_tmp_data))
                    #print('')
                    send_to_ipsc(_network, _tmp_data)
                    time.sleep(0.06)
                self.CALL_DATA = []
        
        
if __name__ == '__main__':
    logger.info('DMRlink \'playback.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = playbackIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network])
    reactor.run()