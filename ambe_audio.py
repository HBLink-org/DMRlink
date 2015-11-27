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
from dmrlink import IPSC, NETWORK, networks, logger, int_id, hex_str_3, get_info, talkgroup_ids, subscriber_ids
import socket
import ConfigParser

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

# Utility function to convert bytes to string of hex values (for debug)
def ByteToHex( byteStr ):
    return ''.join( [ "%02X " % ord(x) for x in byteStr ] ).strip()

#
# Define default values for operation.  These will be overridden by the .cfg file if found
#
_configFile='ambe_audio.cfg'
_debug = False
_outToFile = False
_outToUDP = True
#_gateway = "192.168.1.184"
_gateway = "127.0.0.1"
_gateway_port = 1234
_remote_control_port = 1235
_tg_filter = [2,3,13,3174,3777215,3100,9,9998,3112]  #set this to the tg to monitor
_no_tg = -99


#
# Now read the configuration file and parse out the values we need
#
config = ConfigParser.ConfigParser()
try:
    _tg_filter=[]
    config.read(_configFile)
    for sec in config.sections():
        for key, val in config.items(sec):
            print( '%s="%s"' % (key, val) )
        _debug = config.get(sec, '_debug')
        _outToFile = config.get(sec, '_outToFile')
        _outToUDP = config.get(sec, '_outToUDP')
        _gateway = config.get(sec, '_gateway')
        _gateway_port = config.get(sec, '_gateway_port')
        _tgs = config.get(sec, '_tg_filter')
        _tg_filter = map(int, _tgs.split(','))

except:
    sys.exit('Configuration file \''+_configFile+'\' is not a valid configuration file! Exiting...')


#
# Open output sincs, should be inside of the class....
#
if _outToFile == True:
    f = open('ambe.bin', 'wb')
if _outToUDP == True:
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                     
class ambeIPSC(IPSC):
    _currentTG = _no_tg
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        self._currentTG = _no_tg
        print('DMRLink ambe server')
        print('Send UDP frames to gateway {}:{}'.format(_gateway, _gateway_port))
    
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
        
        _tg_id = int_id(_dst_sub)
        if _tg_id in _tg_filter:    #All TGs
            _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
            if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
                if self._currentTG == _no_tg:
                    if _ts:     _ts = 2
                    else:       _ts = 1
                    _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
                    print('Voice Transmission Start on TS {} and TG {} ({}) from {}'.format(_ts, _dst_sub, _tg_id, _src_sub))
                    self._currentTG = _tg_id
                else:
                    if self._currentTG != _tg_id:
                        print('Transmission in progress, will not decode stream on TG {}'.format(_tg_id))
            if _payload_type == BURST_DATA_TYPE['VOICE_TERM']:
                if self._currentTG == _tg_id:
                    print('Voice Transmission End')
                    self._currentTG = _no_tg
            if _payload_type == BURST_DATA_TYPE['SLOT1_VOICE']:
                if self._currentTG == _tg_id:
                    if _debug == True:
                        print(_ambe_frames)
                        print('Frame 1:', ByteToHex(_ambe_frame1.tobytes()))
                        print('Frame 2:', ByteToHex(_ambe_frame2.tobytes()))
                        print('Frame 3:', ByteToHex(_ambe_frame3.tobytes()))
                
                    if _outToFile == True:
                        f.write( _ambe_frame1.tobytes() )
                        f.write( _ambe_frame2.tobytes() )
                        f.write( _ambe_frame3.tobytes() )
                             
                    if _outToUDP == True:
                        sock.sendto(_ambe_frame1.tobytes(), (_gateway, _gateway_port))
                        sock.sendto(_ambe_frame2.tobytes(), (_gateway, _gateway_port))
                        sock.sendto(_ambe_frame3.tobytes(), (_gateway, _gateway_port))

            
            if _payload_type == BURST_DATA_TYPE['SLOT2_VOICE']:
                if self._currentTG == _tg_id:
                    if _debug == True:
                        print(_ambe_frames)
                        print('Frame 1:', ByteToHex(_ambe_frame1.tobytes()))
                        print('Frame 2:', ByteToHex(_ambe_frame2.tobytes()))
                        print('Frame 3:', ByteToHex(_ambe_frame3.tobytes()))
                    
                    if _outToFile == True:
                        f.write( _ambe_frame1.tobytes() )
                        f.write( _ambe_frame2.tobytes() )
                        f.write( _ambe_frame3.tobytes() )
                    
                    if _outToUDP == True:
                        sock.sendto(_ambe_frame1.tobytes(), (_gateway, _gateway_port))
                        sock.sendto(_ambe_frame2.tobytes(), (_gateway, _gateway_port))
                        sock.sendto(_ambe_frame3.tobytes(), (_gateway, _gateway_port))
        else:
            if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
                _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
                print('Ignored Voice Transmission Start on TS {} and TG {}'.format(_ts, _dst_sub))




import thread

#
# Define a function for the thread
# Use netcat to dynamically change the TGs that are forwarded to Allstar
# echo "x,y,z" | nc 127.0.0.1 1235
#
def remote_control(port):
    s = socket.socket()         # Create a socket object
    host = socket.gethostname() # Get local machine name
    s.bind((host, port))        # Bind to the port
    
    s.listen(5)                 # Now wait for client connection.
    print('listening on port ', host, port)
    while True:
        c, addr = s.accept()     # Establish connection with client.
        print( 'Got connection from', addr )
        tgs = c.recv(1024)
        if tgs:
            _tg_filter = map(int, tgs.split(','))
            print( 'New TGs=', _tg_filter )
        c.close()                # Close the connection
try:
    thread.start_new_thread( remote_control, (_remote_control_port, ) )
except:
    print( "Error: unable to start thread" )



if __name__ == '__main__':
    logger.info('DMRlink \'ambe_audio.py\' (c) 2015 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = ambeIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()
