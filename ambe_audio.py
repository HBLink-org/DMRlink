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

import sys, socket, ConfigParser, thread, traceback
import cPickle as pickle
from dmrlink import IPSC, NETWORK, networks, logger, int_id, hex_str_3, get_info, talkgroup_ids, subscriber_ids
from time import time

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

#
# ambeIPSC class,
#
class ambeIPSC(IPSC):

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
    _sock = -1;
    lastPacketTimeout = 0
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        self.CALL_DATA = []
        
        
        #
        # Define default values for operation.  These will be overridden by the .cfg file if found
        #

        self._currentTG = self._no_tg
        self._sequenceNr = 0
        self.readConfigFile(self._configFile)
    
        print('DMRLink ambe server')

        #
        # Open output sincs
        #
        if self._outToFile == True:
            f = open('ambe.bin', 'wb')
            print('Opening output file: ambe.bin')
        if self._outToUDP == True:
            self._sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            print('Send UDP frames to DMR gateway {}:{}'.format(self._gateway, self._gateway_port))

        try:
            thread.start_new_thread( self.remote_control, (self._remote_control_port, ) )
        except:
            traceback.print_exc()
            print( "Error: unable to start thread" )


    # Utility function to convert bytes to string of hex values (for debug)
    def ByteToHex( self, byteStr ):
        return ''.join( [ "%02X " % ord(x) for x in byteStr ] ).strip()

    #
    # Now read the configuration file and parse out the values we need
    #
    def readConfigFile(self, configFileName):
        config = ConfigParser.ConfigParser()
        try:
            self._tg_filter=[]
            config.read(configFileName)
            for sec in config.sections():
                for key, val in config.items(sec):
                    if self._debug == True:
                        print( '%s="%s"' % (key, val) )
                self._debug = (config.get(sec, '_debug') == "True")
                self._outToFile = (config.get(sec, '_outToFile') == "True")
                self._outToUDP = (config.get(sec, '_outToUDP') == "True")
                self._gateway = config.get(sec, '_gateway')
                self._gateway_port = int(config.get(sec, '_gateway_port'))
                _tgs = config.get(sec, '_tg_filter')
                self._tg_filter = map(int, _tgs.split(','))

        except:
            traceback.print_exc()
            sys.exit('Configuration file \''+configFileName+'\' is not a valid configuration file! Exiting...')

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
        if _tg_id in self._tg_filter:    #All TGs
            _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
            if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
                if self._currentTG == self._no_tg:
                    _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
                    print('Voice Transmission Start on TS {} and TG {} ({}) from {}'.format("2" if _ts else "1", _dst_sub, _tg_id, _src_sub))
                    self._currentTG = _tg_id
                else:
                    if self._currentTG != _tg_id:
                        if time() > self.lastPacketTimeout:
                            self._currentTG = self._no_tg    #looks like we never saw an EOT from the last stream
                            print('EOT timeout')
                        else:
                            print('Transmission in progress, will not decode stream on TG {}'.format(_tg_id))
            if self._currentTG == _tg_id:
                if _payload_type == BURST_DATA_TYPE['VOICE_TERM']:
                    print('Voice Transmission End')
                    self._currentTG = self._no_tg
                if _payload_type == BURST_DATA_TYPE['SLOT1_VOICE']:
                    self.outputFrames(_ambe_frames, _ambe_frame1, _ambe_frame2, _ambe_frame3)
                if _payload_type == BURST_DATA_TYPE['SLOT2_VOICE']:
                    self.outputFrames(_ambe_frames, _ambe_frame1, _ambe_frame2, _ambe_frame3)
                self.lastPacketTimeout = time() + 10
    
        else:
            if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
                _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
                print('Ignored Voice Transmission Start on TS {} and TG {}'.format("2" if _ts else "1", _dst_sub))

    def outputFrames(self, _ambe_frames, _ambe_frame1, _ambe_frame2, _ambe_frame3):
        if self._debug == True:
            print(_ambe_frames)
            print('Frame 1:', self.ByteToHex(_ambe_frame1.tobytes()))
            print('Frame 2:', self.ByteToHex(_ambe_frame2.tobytes()))
            print('Frame 3:', self.ByteToHex(_ambe_frame3.tobytes()))

        if self._outToFile == True:
            f.write( _ambe_frame1.tobytes() )
            f.write( _ambe_frame2.tobytes() )
            f.write( _ambe_frame3.tobytes() )

        if self._outToUDP == True:
            self._sock.sendto(_ambe_frame1.tobytes(), (self._gateway, self._gateway_port))
            self._sock.sendto(_ambe_frame2.tobytes(), (self._gateway, self._gateway_port))
            self._sock.sendto(_ambe_frame3.tobytes(), (self._gateway, self._gateway_port))



    #
    # Define a function for the thread
    # Use netcat to dynamically change the TGs that are forwarded to Allstar
    # echo "x,y,z" | nc 127.0.0.1 1235
    #
    def remote_control(self, port):
        s = socket.socket()         # Create a socket object
        host = socket.gethostname() # Get local machine name
        s.bind((host, port))        # Bind to the port
        
        s.listen(5)                 # Now wait for client connection.
        print('Remote control is listening on:', host, port)
        while True:
            c, addr = s.accept()     # Establish connection with client.
            print( 'Got connection from', addr )
            tgs = c.recv(1024)
            if tgs:
                self._tg_filter = map(int, tgs.split(','))
                print( 'New TGs=', self._tg_filter )
            c.close()                # Close the connection



if __name__ == '__main__':
    logger.info('DMRlink \'ambe_audio.py\' (c) 2015 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = ambeIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()
