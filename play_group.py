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
from dmrlink import IPSC, NETWORK, networks, logger, int_id, hex_str_3, send_to_ipsc

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK; Dave K; and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'pre-alpha'

filename = '../../test.ipsc'

class playIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        if _end:
            if True:
                time.sleep(2)
                self.CALL_DATA = pickle.load(open(filename, 'rb'))
                for i in self.CALL_DATA:
                    _tmp_data = i
                    _tmp_data = _tmp_data.replace(_peerid, NETWORK[_network]['LOCAL']['RADIO_ID'])
                    _tmp_data = self.hashed_packet(NETWORK[_network]['LOCAL']['AUTH_KEY'], _tmp_data)
                    # Send the packet to all peers in the target IPSC
                    send_to_ipsc(_network, _tmp_data)
                    time.sleep(0.06)
                self.CALL_DATA = []
        
if __name__ == '__main__':
    logger.info('DMRlink \'record.py\' (c) 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = playIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network])
    reactor.run()
