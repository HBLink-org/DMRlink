#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample applicaiton that dumps all raw AMBE+2 voice frame data
# It is useful for things like, decoding the audio stream with a DVSI dongle, etc.

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h
from bitstring import BitArray

import sys
import cPickle as pickle
from dmrlink import IPSC, NETWORK, networks, logger, int_id, hex_str_3

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2015 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK; Robert Garcia, N5QM'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__maintainer__ = 'Cort Buffington, N0MJS'
__version__ = '0.1a'
__email__ = 'n0mjs@me.com'
__status__ = 'pre-alpha'

try:
    from ipsc.ipsc_message_types import *
except ImportError:
    sys.exit('IPSC message types file not found or invalid')
    

class ambeIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #

    def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        # THIS FUNCTION IS NOT COMPLETE!!!!
        _payload_type = _data[30:31]
        # _ambe_frames = _data[33:52]
        _ambe_frames = BitArray('0x'+h(_data[33:52]))
        _ambe_frame1 = _ambe_frames[0:49]
        _ambe_frame2 = _ambe_frames[50:99]
        _ambe_frame3 = _ambe_frames[100:149]
        
        if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
            print('Voice Transmission Start')
        if _payload_type == BURST_DATA_TYPE['VOICE_TERM']:
            print('Voice Transmission End')
        if _payload_type == BURST_DATA_TYPE['SLOT1_VOICE']:
            print(_ambe_frames)
            print('Frame 1:', _ambe_frame1.bytes)
            print('Frame 2:', _ambe_frame2.bytes)
            print('Frame 3:', _ambe_frame3.bytes)
        if _payload_type == BURST_DATA_TYPE['SLOT2_VOICE']:
            print(_ambe_frames)
            print('Frame 1:', _ambe_frame1.bytes)
            print('Frame 2:', _ambe_frame2.bytes)
            print('Frame 3:', _ambe_frame3.bytes)

        
if __name__ == '__main__':
    logger.info('DMRlink \'ambe_audio.py\' (c) 2015 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = ambeIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()
