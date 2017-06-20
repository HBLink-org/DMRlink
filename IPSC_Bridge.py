#!/usr/bin/env python
#
###############################################################################
#   Copyright (C) 2016  Cortney T. Buffington, N0MJS <n0mjs@me.com>
#   and
#   Copyright (C) 2017  Mike Zingman, N4IRR <Not.A.Chance@NoWhere.com>
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

# This is a bridge application for IPSC networks.  It knows how to export AMBE
# frames and metadata to an external program/network.  It also knows how to import
# AMBE and metadata from an external network and send the DMR frames to IPSC networks.

#####################################################################################################

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h
from bitstring import BitArray

import sys, socket, ConfigParser, thread, traceback
import cPickle as pickle

from dmrlink import IPSC, systems, config_reports, reportFactory 
from dmr_utils.utils import int_id, hex_str_3, hex_str_4, get_alias, get_info

from time import time, sleep, clock, localtime, strftime
import csv
import struct
from random import randint
from dmr_utils import ambe_utils
from dmr_utils.ambe_bridge import AMBE_IPSC

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013 - 2016 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF; Robert Garcia, N5QM; Steve Zingman, N4IRS; Mike Zingman, N4IRR'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'
__version__    = '20170620'


try:
    from ipsc.ipsc_const import *
except ImportError:
    sys.exit('IPSC constants file not found or invalid')

try:
    from ipsc.ipsc_mask import *
except ImportError:
    sys.exit('IPSC mask values file not found or invalid')


#
# ambeIPSC class,
#
class ambeIPSC(IPSC):

    _configFile='IPSC_Bridge.cfg'                        # Name of the config file to over-ride these default values
    _debug = False                                      # Debug output for each VOICE frame
    _outToFile = False                                  # Write each AMBE frame to a file called ambe.bin
    _outToUDP = True                                    # Send each AMBE frame to the _sock object (turn on/off Analog_Bridge operation)
    _gateway = "127.0.0.1"                              # IP address of  app
    _gateway_port = 31000                               # Port Analog_Bridge is listening on for AMBE frames to decode
    _remote_control_port = 31002                        # Port that ambe_audio is listening on for remote control commands
    _ambeRxPort = 31003                                 # Port to listen on for AMBE frames to transmit to all peers
    _gateway_dmr_id = 0                                 # id to use when transmitting from the gateway
    _tg_filter = [2,3,13,3174,3777215,3100,9,9998,3112]  #set this to the tg to monitor
    
    _no_tg = -99                                        # Flag (const) that defines a value for "no tg is currently active"
    _busy_slots = [0,0,0]                               # Keep track of activity on each slot.  Make sure app is polite
    _sock = -1;                                         # Socket object to send AMBE to Analog_Bridge
    lastPacketTimeout = 0                               # Time of last packet. Used to trigger an artifical TERM if one was not seen
    _transmitStartTime = 0                              # Used for info on transmission duration
    _start_seq = 0                                      # Used to maintain error statistics for a transmission
    _packet_count = 0                                   # Used to maintain error statistics for a transmission
    _seq = 0                                            # Transmit frame sequence number (auto-increments for each frame)
    _f = None                                           # File handle for debug AMBE binary output

    _tx_tg = hex_str_3(9998)                            # Hard code the destination TG.  This ensures traffic will not show up on DMR-MARC
    _tx_ts = 2                                          # Time Slot 2
    _currentNetwork = ""
    _dmrgui = ''
    cc = 1
    ipsc_seq = 0

    ###### DEBUGDEBUGDEBUG
    #_d = None
    ###### DEBUGDEBUGDEBUG
    
    def __init__(self, _name, _config, _logger, _report):
        IPSC.__init__(self, _name, _config, _logger, _report)
        self.CALL_DATA = []
        
        #
        # Define default values for operation.  These will be overridden by the .cfg file if found
        #
        
        self._currentTG = self._no_tg
        self._currentNetwork = str(_name)
        self.readConfigFile(self._configFile, None, self._currentNetwork)
    
        logger.info('DMRLink IPSC Bridge')
        if self._gateway_dmr_id == 0:
            sys.exit( "Error: gatewayDmrId must be set (greater than zero)" )

        #
        # Open output sincs
        #
        if self._outToFile == True:
            self._f = open('ambe.bin', 'wb')
            logger.info('Opening output file: ambe.bin')
        if self._outToUDP == True:
            self._sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            logger.info('Send UDP frames to Partner Bridge {}:{}'.format(self._gateway, self._gateway_port))
        
        self.ipsc_ambe = AMBE_IPSC(self, _name, _config, _logger, self._ambeRxPort)

    def get_globals(self):
        return (subscriber_ids, talkgroup_ids, peer_ids)

    def get_repeater_id(self, import_id):
        return self._config['LOCAL']['RADIO_ID']

    # Utility function to convert bytes to string of hex values (for debug)
    def ByteToHex( self, byteStr ):
        return ''.join( [ "%02X " % ord(x) for x in byteStr ] ).strip()

    #
    # Now read the configuration file and parse out the values we need
    #
    def defaultOption( self, config, sec, opt, defaultValue ):
        try:
            _value = config.get(sec, opt).split(None)[0]            # Get the value from the named section
        except ConfigParser.NoOptionError as e:
            try:
                _value = config.get('DEFAULTS', opt).split(None)[0] # Try the global DEFAULTS section
            except ConfigParser.NoOptionError as e:
                _value = defaultValue                               # Not found anywhere, use the default value
        logger.info(opt + ' = ' + str(_value))
        return _value

    def readConfigFile(self, configFileName, sec, networkName='DEFAULTS'):
        config = ConfigParser.ConfigParser()
        try:
            config.read(configFileName)
            
            if sec == None:
                sec = self.defaultOption(config, 'DEFAULTS', 'section', networkName)
            if config.has_section(sec) == False:
                logger.info('Section ' + sec + ' was not found, using DEFAULTS')
                sec = 'DEFAULTS'
            self._debug = bool(self.defaultOption(config, sec,'debug', self._debug) == 'True')
            self._outToFile = bool(self.defaultOption(config, sec,'outToFile', self._outToFile) == 'True')
            self._outToUDP = bool(self.defaultOption(config, sec,'outToUDP', self._outToUDP) == 'True')

            self._gateway = self.defaultOption(config, sec,'gateway', self._gateway)
            self._gateway_port = int(self.defaultOption(config, sec,'toGatewayPort', self._gateway_port))

            self._remote_control_port = int(self.defaultOption(config, sec,'remoteControlPort', self._remote_control_port))
            self._ambeRxPort = int(self.defaultOption(config, sec,'fromGatewayPort', self._ambeRxPort))
            self._gateway_dmr_id = int(self.defaultOption(config, sec, 'gatewayDmrId', self._gateway_dmr_id))

            _tgs = self.defaultOption(config, sec,'tgFilter', str(self._tg_filter).strip('[]'))
            self._tg_filter = map(int, _tgs.split(','))

            self._tx_tg = hex_str_3(int(self.defaultOption(config, sec, 'txTg', int_id(self._tx_tg))))
            self._tx_ts = int(self.defaultOption(config, sec, 'txTs', self._tx_ts))

        except ConfigParser.NoOptionError as e:
            print('Using a default value:', e)
        except:
            traceback.print_exc()
            sys.exit('Configuration file \''+configFileName+'\' is not a valid configuration file! Exiting...')

    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #

    def group_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        _tx_slot = self.ipsc_ambe.tx[_ts]
        _payload_type = _data[30:31]
        _seq = int_id(_data[20:22])
        _tx_slot.frame_count += 1
        if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
            _stream_id       = int_id(_data[5:6])                 # int8  looks like a sequence number for a packet
            if (_stream_id != _tx_slot.stream_id):
                self.ipsc_ambe.begin_call(_ts, _src_sub, _dst_sub, _peerid, self.cc, _seq, _stream_id)
            _tx_slot.lastSeq = _seq
        if _payload_type == BURST_DATA_TYPE['VOICE_TERM']:
            self.ipsc_ambe.end_call(_tx_slot)
        if (_payload_type == BURST_DATA_TYPE['SLOT1_VOICE']) or (_payload_type == BURST_DATA_TYPE['SLOT2_VOICE']):
            _ambe_frames = BitArray('0x'+h(_data[33:52]))
            _ambe_frame1 = _ambe_frames[0:49]
            _ambe_frame2 = _ambe_frames[50:99]
            _ambe_frame3 = _ambe_frames[100:149]
            self.ipsc_ambe.export_voice(_tx_slot, _seq, _ambe_frame1.tobytes() + _ambe_frame2.tobytes() + _ambe_frame3.tobytes())


    def private_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        print('private voice')

    #************************************************
    #     Debug: print IPSC frame on console
    #************************************************
    def dumpIPSCFrame( self, _frame ):
        
        _packettype     = int_id(_frame[0:1])                 # int8  GROUP_VOICE, PVT_VOICE, GROUP_DATA, PVT_DATA, CALL_MON_STATUS, CALL_MON_RPT, CALL_MON_NACK, XCMP_XNL, RPT_WAKE_UP, DE_REG_REQ
        _peerid         = int_id(_frame[1:5])                 # int32 peer who is sending us a packet
        _ipsc_seq       = int_id(_frame[5:6])                 # int8  looks like a sequence number for a packet
        _src_sub        = int_id(_frame[6:9])                 # int32 Id of source
        _dst_sub        = int_id(_frame[9:12])                # int32 Id of destination
        _call_type      = int_id(_frame[12:13])               # int8 Priority Voice/Data
        _call_ctrl_info  = int_id(_frame[13:17])              # int32
        _call_info      = int_id(_frame[17:18])               # int8  Bits 6 and 7 defined as TS and END
        
        # parse out the RTP values
        _rtp_byte_1 = int_id(_frame[18:19])                 # Call Ctrl Src
        _rtp_byte_2 = int_id(_frame[19:20])                 # Type
        _rtp_seq    = int_id(_frame[20:22])                 # Call Seq No
        _rtp_tmstmp = int_id(_frame[22:26])                 # Timestamp
        _rtp_ssid   = int_id(_frame[26:30])                 # Sync Src Id
        
        _payload_type   = _frame[30]                       # int8  VOICE_HEAD, VOICE_TERM, SLOT1_VOICE, SLOT2_VOICE
        
        _ts             = bool(_call_info & TS_CALL_MSK)
        _end            = bool(_call_info & END_MSK)

        if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
            print('HEAD:', h(_frame))
        if _payload_type == BURST_DATA_TYPE['VOICE_TERM']:
            
            _ipsc_rssi_threshold_and_parity = int_id(_frame[31])
            _ipsc_length_to_follow = int_id(_frame[32:34])
            _ipsc_rssi_status = int_id(_frame[34])
            _ipsc_slot_type_sync = int_id(_frame[35])
            _ipsc_data_size = int_id(_frame[36:38])
            _ipsc_data = _frame[38:38+(_ipsc_length_to_follow * 2)-4]
            _ipsc_full_lc_byte1 = int_id(_frame[38])
            _ipsc_full_lc_fid = int_id(_frame[39])
            _ipsc_voice_pdu_service_options = int_id(_frame[40])
            _ipsc_voice_pdu_dst = int_id(_frame[41:44])
            _ipsc_voice_pdu_src = int_id(_frame[44:47])

            print('{} {} {} {} {} {} {} {} {} {} {}'.format(_ipsc_rssi_threshold_and_parity,_ipsc_length_to_follow,_ipsc_rssi_status,_ipsc_slot_type_sync,_ipsc_data_size,h(_ipsc_data),_ipsc_full_lc_byte1,_ipsc_full_lc_fid,_ipsc_voice_pdu_service_options,_ipsc_voice_pdu_dst,_ipsc_voice_pdu_src))
            print('TERM:', h(_frame))
        if _payload_type == BURST_DATA_TYPE['SLOT1_VOICE']:
            _rtp_len        = _frame[31:32]
            _ambe           = _frame[33:52]
            print('SLOT1:', h(_frame))
        if _payload_type == BURST_DATA_TYPE['SLOT2_VOICE']:
            _rtp_len        = _frame[31:32]
            _ambe           = _frame[33:52]
            print('SLOT2:', h(_frame))
        print("pt={:02X} pid={} seq={:02X} src={} dst={} ct={:02X} uk={} ci={} rsq={}".format(_packettype, _peerid,_ipsc_seq, _src_sub,_dst_sub,_call_type,_call_ctrl_info,_call_info,_rtp_seq))
    
if __name__ == '__main__':
    import argparse
    import os
    import sys
    import signal
    from dmr_utils.utils import try_download, mk_id_dict

    from ipsc.dmrlink_log import config_logging    
    from ipsc.dmrlink_config import build_config
    
    # Change the current directory to the location of the application
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    # CLI argument parser - handles picking up the config file from the command line, and sending a "help" message
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action='store', dest='CFG_FILE', help='/full/path/to/config.file (usually dmrlink.cfg)')
    parser.add_argument('-ll', '--log_level', action='store', dest='LOG_LEVEL', help='Override config file logging level.')
    parser.add_argument('-lh', '--log_handle', action='store', dest='LOG_HANDLERS', help='Override config file logging handler.')
    cli_args = parser.parse_args()

    if not cli_args.CFG_FILE:
        cli_args.CFG_FILE = os.path.dirname(os.path.abspath(__file__))+'/dmrlink.cfg'
    
    # Call the external routine to build the configuration dictionary
    CONFIG = build_config(cli_args.CFG_FILE)
    
    # Call the external routing to start the system logger
    if cli_args.LOG_LEVEL:
        CONFIG['LOGGER']['LOG_LEVEL'] = cli_args.LOG_LEVEL
    if cli_args.LOG_HANDLERS:
        CONFIG['LOGGER']['LOG_HANDLERS'] = cli_args.LOG_HANDLERS
    logger = config_logging(CONFIG['LOGGER'])  

    logger.info('DMRlink \'IPSC_Bridge.py\' (c) 2015 N0MJS & the K0USY Group - SYSTEM STARTING...')
    logger.info('Version %s', __version__)

    # ID ALIAS CREATION
    # Download
    if CONFIG['ALIASES']['TRY_DOWNLOAD'] == True:
        # Try updating peer aliases file
        result = try_download(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['PEER_FILE'], CONFIG['ALIASES']['PEER_URL'], CONFIG['ALIASES']['STALE_TIME'])
        logger.info(result)
        # Try updating subscriber aliases file
        result = try_download(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['SUBSCRIBER_FILE'], CONFIG['ALIASES']['SUBSCRIBER_URL'], CONFIG['ALIASES']['STALE_TIME'])
        logger.info(result)
        
    # Make Dictionaries
    peer_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['PEER_FILE'])
    if peer_ids:
        logger.info('ID ALIAS MAPPER: peer_ids dictionary is available')
        
    subscriber_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['SUBSCRIBER_FILE'])
    if subscriber_ids:
        logger.info('ID ALIAS MAPPER: subscriber_ids dictionary is available')
    
    talkgroup_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['TGID_FILE'])
    if talkgroup_ids:
        logger.info('ID ALIAS MAPPER: talkgroup_ids dictionary is available')
    
    # Shut ourselves down gracefully with the IPSC peers.
    def sig_handler(_signal, _frame):
        logger.info('*** DMRLINK IS TERMINATING WITH SIGNAL %s ***', str(_signal))
    
        for system in systems:
            this_ipsc = systems[system]
            logger.info('De-Registering from IPSC %s', system)
            de_reg_req_pkt = this_ipsc.hashed_packet(this_ipsc._local['AUTH_KEY'], this_ipsc.DE_REG_REQ_PKT)
            this_ipsc.send_to_ipsc(de_reg_req_pkt)
        reactor.stop()

    # Set signal handers so that we can gracefully exit if need be
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
        signal.signal(sig, sig_handler)

    # INITIALIZE THE REPORTING LOOP
    report_server = config_reports(CONFIG, logger, reportFactory)

    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGUED IPSC
    for system in CONFIG['SYSTEMS']:
        if CONFIG['SYSTEMS'][system]['LOCAL']['ENABLED']:
            systems[system] = ambeIPSC(system, CONFIG, logger, report_server)
            reactor.listenUDP(CONFIG['SYSTEMS'][system]['LOCAL']['PORT'], systems[system], interface=CONFIG['SYSTEMS'][system]['LOCAL']['IP'])
    
    reactor.run()


