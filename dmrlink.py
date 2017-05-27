#!/usr/bin/env python
#
###############################################################################
#   Copyright (C) 2016  Cortney T. Buffington, N0MJS <n0mjs@me.com>
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

#NOTE: This program uses a configuration file specified on the command line
#      if none is specified, then dmrlink.cfg in the same directory as this
#      file will be tried. Finally, if that does not exist, this process
#      will terminate

from __future__ import print_function

# Full imports
import logging
import cPickle as pickle

# Function Imports
from hmac import new as hmac_new
from binascii import b2a_hex as ahex
from binascii import a2b_hex as bhex
from hashlib import sha1
from socket import inet_ntoa as IPAddr
from socket import inet_aton as IPHexStr
from time import time

# Twisted Imports
from twisted.internet.protocol import DatagramProtocol, Factory, Protocol
from twisted.protocols.basic import NetstringReceiver
from twisted.internet import reactor, task

# Imports files in the dmrlink subdirectory (these things shouldn't change often)
from ipsc.ipsc_const import *
from ipsc.ipsc_mask import *
from ipsc.reporting_const import *

# Imports from DMR Utilities package
from dmr_utils.utils import hex_str_2, hex_str_3, hex_str_4, int_id, try_download, mk_id_dict


__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013 - 2016 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF; Steve Zingman, N4IRS; Mike Zingman, N4IRR'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


# Global variables used whether we are a module or __main__
systems = {}


# Timed loop used for reporting IPSC status
#
# REPORT BASED ON THE TYPE SELECTED IN THE MAIN CONFIG FILE
def config_reports(_config, _logger, _factory): 
    if _config['REPORTS']['REPORT_NETWORKS'] == 'PRINT':
        def reporting_loop(_logger):
            _logger.debug('Periodic Reporting Loop Started (PRINT)')
            for system in _config['SYSTEMS']:
                print_master(_config, system)
                print_peer_list(_config, system)
        
        reporting = task.LoopingCall(reporting_loop, _logger)
        reporting.start(_config['REPORTS']['REPORT_INTERVAL'])
        report_server = False
                
    elif _config['REPORTS']['REPORT_NETWORKS'] == 'NETWORK':
        def reporting_loop(_logger, _server):
            _logger.debug('Periodic Reporting Loop Started (NETWORK)')
            _server.send_config()
            
        _logger.info('DMRlink TCP reporting server starting')
        
        report_server = _factory(_config, _logger)
        report_server.clients = []
        reactor.listenTCP(_config['REPORTS']['REPORT_PORT'], report_server)
        
        reporting = task.LoopingCall(reporting_loop, _logger, report_server)
        reporting.start(_config['REPORTS']['REPORT_INTERVAL'])

    else:
        def reporting_loop(_logger):
            _logger.debug('Periodic Reporting Loop Started (NULL)')
        report_server = False
    
    return report_server


# ID ALIAS CREATION
# Download
def build_aliases(_config, _logger):
    if _config['ALIASES']['TRY_DOWNLOAD'] == True:
        # Try updating peer aliases file
        result = try_download(_config['ALIASES']['PATH'], _config['ALIASES']['PEER_FILE'], _config['ALIASES']['PEER_URL'], _config['ALIASES']['STALE_TIME'])
        _logger.info(result)
        # Try updating subscriber aliases file
        result = try_download(_config['ALIASES']['PATH'], _config['ALIASES']['SUBSCRIBER_FILE'], _config['ALIASES']['SUBSCRIBER_URL'], _config['ALIASES']['STALE_TIME'])
        _logger.info(result)
        
    # Make Dictionaries
    peer_ids = mk_id_dict(_config['ALIASES']['PATH'], _config['ALIASES']['PEER_FILE'])
    if peer_ids:
        _logger.info('ID ALIAS MAPPER: peer_ids dictionary is available')
        
    subscriber_ids = mk_id_dict(_config['ALIASES']['PATH'], _config['ALIASES']['SUBSCRIBER_FILE'])
    if subscriber_ids:
        _logger.info('ID ALIAS MAPPER: subscriber_ids dictionary is available')
    
    talkgroup_ids = mk_id_dict(_config['ALIASES']['PATH'], _config['ALIASES']['TGID_FILE'])
    if talkgroup_ids:
        _logger.info('ID ALIAS MAPPER: talkgroup_ids dictionary is available')
        
    local_ids = mk_id_dict(_config['ALIASES']['PATH'], _config['ALIASES']['LOCAL_FILE'])
    if local_ids:
        _logger.info('ID ALIAS MAPPER: local_ids dictionary is available')

    return(peer_ids, subscriber_ids, talkgroup_ids, local_ids)


# Make the IPSC systems from the config and the class used to build them.
#
def mk_ipsc_systems(_config, _logger, _systems, _ipsc, _report_server):
    for system in _config['SYSTEMS']:
        if _config['SYSTEMS'][system]['LOCAL']['ENABLED']:
            _systems[system] = _ipsc(system, _config, _logger, _report_server)
            reactor.listenUDP(_config['SYSTEMS'][system]['LOCAL']['PORT'], _systems[system], interface=_config['SYSTEMS'][system]['LOCAL']['IP'])
    return _systems

# Process the MODE byte in registration/peer list packets for determining master and peer capabilities
#
def process_mode_byte(_hex_mode):
    _mode = int(ahex(_hex_mode), 16)
    
    # Determine whether or not the peer is operational
    _peer_op = bool(_mode & PEER_OP_MSK)    
    # Determine whether or not timeslot 1 is linked
    _ts1 = bool(_mode & IPSC_TS1_MSK)  
    # Determine whether or not timeslot 2 is linked
    _ts2 = bool(_mode & IPSC_TS2_MSK)
     
    # Determine the operational mode of the peer
    if _mode & PEER_MODE_MSK == PEER_MODE_MSK:
        _peer_mode = 'UNKNOWN'
    elif not _mode & PEER_MODE_MSK:
        _peer_mode = 'NO_RADIO'
    elif _mode & PEER_MODE_ANALOG:
        _peer_mode = 'ANALOG'
    elif _mode & PEER_MODE_DIGITAL:
        _peer_mode = 'DIGITAL'
    
    return {
        'PEER_OP': _peer_op,
        'PEER_MODE': _peer_mode,
        'TS_1': _ts1,
        'TS_2': _ts2
        }

# Process the FLAGS bytes in registration replies for determining what services are available
#
def process_flags_bytes(_hex_flags):
    _byte3 = int(ahex(_hex_flags[2]), 16)
    _byte4 = int(ahex(_hex_flags[3]), 16)
    
    _csbk       = bool(_byte3 & CSBK_MSK)
    _rpt_mon    = bool(_byte3 & RPT_MON_MSK)
    _con_app    = bool(_byte3 & CON_APP_MSK)
    _xnl_con    = bool(_byte4 & XNL_STAT_MSK)
    _xnl_master = bool(_byte4 & XNL_MSTR_MSK)
    _xnl_slave  = bool(_byte4 & XNL_SLAVE_MSK)
    _auth       = bool(_byte4 & PKT_AUTH_MSK)
    _data       = bool(_byte4 & DATA_CALL_MSK)
    _voice      = bool(_byte4 & VOICE_CALL_MSK)
    _master     = bool(_byte4 & MSTR_PEER_MSK)
    
    return {
        'CSBK': _csbk,
        'RCM': _rpt_mon,
        'CON_APP': _con_app,
        'XNL_CON': _xnl_con,
        'XNL_MASTER': _xnl_master,
        'XNL_SLAVE': _xnl_slave,
        'AUTH': _auth,
        'DATA': _data,
        'VOICE': _voice,
        'MASTER': _master
        } 

# Build a peer list - used when a peer registers, re-regiseters or times out
#
def build_peer_list(_peers):
    concatenated_peers = ''
    for peer in _peers:
        hex_ip = IPHexStr(_peers[peer]['IP'])
        hex_port = hex_str_2(_peers[peer]['PORT'])
        mode = _peers[peer]['MODE']        
        concatenated_peers += peer + hex_ip + hex_port + mode
    
    peer_list = hex_str_2(len(concatenated_peers)) + concatenated_peers
    
    return peer_list

# Gratuitous print-out of the peer list.. Pretty much debug stuff.
#
def print_peer_list(_config, _network):
    _peers = _config['SYSTEMS'][_network]['PEERS']
    
    _status = _config['SYSTEMS'][_network]['MASTER']['STATUS']['PEER_LIST']
    #print('Peer List Status for {}: {}' .format(_network, _status))
    
    if _status and not _config['SYSTEMS'][_network]['PEERS']:
        print('We are the only peer for: %s' % _network)
        print('')
        return
             
    print('Peer List for: %s' % _network)
    for peer in _peers.keys():
        _this_peer = _peers[peer]
        _this_peer_stat = _this_peer['STATUS']
        
        if peer == _config['SYSTEMS'][_network]['LOCAL']['RADIO_ID']:
            me = '(self)'
        else:
            me = ''
             
        print('\tRADIO ID: {} {}' .format(int_id(peer), me))
        print('\t\tIP Address: {}:{}' .format(_this_peer['IP'], _this_peer['PORT']))
        if _this_peer['MODE_DECODE'] and _config['REPORTS']['PRINT_PEERS_INC_MODE']:
            print('\t\tMode Values:')
            for name, value in _this_peer['MODE_DECODE'].items():
                print('\t\t\t{}: {}' .format(name, value))
        if _this_peer['FLAGS_DECODE'] and _config['REPORTS']['PRINT_PEERS_INC_FLAGS']:
            print('\t\tService Flags:')
            for name, value in _this_peer['FLAGS_DECODE'].items():
                print('\t\t\t{}: {}' .format(name, value))
        print('\t\tStatus: {},  KeepAlives Sent: {},  KeepAlives Outstanding: {},  KeepAlives Missed: {}' .format(_this_peer_stat['CONNECTED'], _this_peer_stat['KEEP_ALIVES_SENT'], _this_peer_stat['KEEP_ALIVES_OUTSTANDING'], _this_peer_stat['KEEP_ALIVES_MISSED']))
        print('\t\t                KeepAlives Received: {},  Last KeepAlive Received at: {}' .format(_this_peer_stat['KEEP_ALIVES_RECEIVED'], _this_peer_stat['KEEP_ALIVE_RX_TIME']))
        
    print('')
 
# Gratuitous print-out of Master info.. Pretty much debug stuff.
#
def print_master(_config, _network):
    if _config['SYSTEMS'][_network]['LOCAL']['MASTER_PEER']:
        print('DMRlink is the Master for %s' % _network)
    else:
        _master = _config['SYSTEMS'][_network]['MASTER']
        print('Master for %s' % _network)
        print('\tRADIO ID: {}' .format(int(ahex(_master['RADIO_ID']), 16)))
        if _master['MODE_DECODE'] and _config['REPORTS']['PRINT_PEERS_INC_MODE']:
            print('\t\tMode Values:')
            for name, value in _master['MODE_DECODE'].items():
                print('\t\t\t{}: {}' .format(name, value))
        if _master['FLAGS_DECODE'] and _config['REPORTS']['PRINT_PEERS_INC_FLAGS']:
            print('\t\tService Flags:')
            for name, value in _master['FLAGS_DECODE'].items():
                print('\t\t\t{}: {}' .format(name, value))
        print('\t\tStatus: {},  KeepAlives Sent: {},  KeepAlives Outstanding: {},  KeepAlives Missed: {}' .format(_master['STATUS']['CONNECTED'], _master['STATUS']['KEEP_ALIVES_SENT'], _master['STATUS']['KEEP_ALIVES_OUTSTANDING'], _master['STATUS']['KEEP_ALIVES_MISSED']))
        print('\t\t                KeepAlives Received: {},  Last KeepAlive Received at: {}' .format(_master['STATUS']['KEEP_ALIVES_RECEIVED'], _master['STATUS']['KEEP_ALIVE_RX_TIME']))
    


#************************************************
#     IPSC CLASS
#************************************************

class IPSC(DatagramProtocol):
    def __init__(self, _name, _config, _logger, _report):

        # Housekeeping: create references to the configuration and status data for this IPSC instance.
        # Some configuration objects that are used frequently and have lengthy names are shortened
        # such as (self._master_sock) expands to (self._config['MASTER']['IP'], self._config['MASTER']['PORT']).
        # Note that many of them reference each other... this is the Pythonic way.
        #
        self._system = _name
        self._CONFIG = _config
        self._logger = _logger
        self._report = _report
        self._config = self._CONFIG['SYSTEMS'][self._system]
        self._rcm = self._CONFIG['REPORTS']['REPORT_RCM'] and self._report
        #
        self._local = self._config['LOCAL']
        self._local_id = self._local['RADIO_ID']
        #
        self._master = self._config['MASTER']
        self._master_stat = self._master['STATUS']
        self._master_sock = self._master['IP'], self._master['PORT']
        #
        self._peers = self._config['PEERS']
        #
        # This is a regular list to store peers for the IPSC. At times, parsing a simple list is much less
        # Spendy than iterating a list of dictionaries... Maybe I'll find a better way in the future. Also
        # We have to know when we have a new peer list, so a variable to indicate we do (or don't)
        #
        args = ()
        
        # Packet 'constructors' - builds the necessary control packets for this IPSC instance.
        # This isn't really necessary for anything other than readability (reduction of code golf)
        #
        # General Items
        self.TS_FLAGS               = (self._local['MODE'] + self._local['FLAGS'])
        #
        # Peer Link Maintenance Packets 
        self.MASTER_REG_REQ_PKT     = (MASTER_REG_REQ + self._local_id + self.TS_FLAGS + IPSC_VER)
        self.MASTER_ALIVE_PKT       = (MASTER_ALIVE_REQ + self._local_id + self.TS_FLAGS + IPSC_VER)
        self.PEER_LIST_REQ_PKT      = (PEER_LIST_REQ + self._local_id)
        self.PEER_REG_REQ_PKT       = (PEER_REG_REQ + self._local_id + IPSC_VER)
        self.PEER_REG_REPLY_PKT     = (PEER_REG_REPLY + self._local_id + IPSC_VER)
        self.PEER_ALIVE_REQ_PKT     = (PEER_ALIVE_REQ + self._local_id + self.TS_FLAGS)
        self.PEER_ALIVE_REPLY_PKT   = (PEER_ALIVE_REPLY + self._local_id + self.TS_FLAGS)
        #
        # Master Link Maintenance Packets
        # self.MASTER_REG_REPLY_PKT   is not static and must be generated when it is sent
        self.MASTER_ALIVE_REPLY_PKT = (MASTER_ALIVE_REPLY + self._local_id + self.TS_FLAGS + IPSC_VER)
        self.PEER_LIST_REPLY_PKT    = (PEER_LIST_REPLY + self._local_id)
        #
        # General Link Maintenance Packets
        self.DE_REG_REQ_PKT         = (DE_REG_REQ + self._local_id)
        self.DE_REG_REPLY_PKT       = (DE_REG_REPLY + self._local_id)
        #
        self._logger.info('(%s) IPSC Instance Created: %s, %s:%s', self._system, int_id(self._local['RADIO_ID']), self._local['IP'], self._local['PORT'])


    #******************************************************
    #     SUPPORT FUNCTIONS FOR HANDLING IPSC OPERATIONS
    #******************************************************
    
    # Determine if the provided peer ID is valid for the provided network 
    #
    def valid_peer(self, _peerid):
        if _peerid in self._peers:
            return True        
        return False
    
    # Determine if the provided master ID is valid for the provided network
    #
    def valid_master(self, _peerid):
        if self._master['RADIO_ID'] == _peerid:
            return True     
        else:
            return False

    # De-register a peer from an IPSC by removing it's information
    #
    def de_register_peer(self, _peerid):
        # Iterate for the peer in our data
        if _peerid in self._peers.keys():
            del self._peers[_peerid]
            self._logger.info('(%s) Peer De-Registration Requested for: %s', self._system, int_id(_peerid))
            return
        else:
            self._logger.warning('(%s) Peer De-Registration Requested for: %s, but we don\'t have a listing for this peer', self._system, int_id(_peerid))
            pass
            
    # De-register ourselves from the IPSC
    def de_register_self(self):
        self._logger.info('(%s) De-Registering self from the IPSC system', self._system)
        de_reg_req_pkt = self.hashed_packet(self._local['AUTH_KEY'], self.DE_REG_REQ_PKT)
        self.send_to_ipsc(de_reg_req_pkt)
    
    # Take a received peer list and the network it belongs to, process and populate the
    # data structure in my_ipsc_config with the results, and return a simple list of peers.
    #
    def process_peer_list(self, _data):
        # Create a temporary peer list to track who we should have in our list -- used to find old peers we should remove.
        _temp_peers = []
        # Determine the length of the peer list for the parsing iterator
        _peer_list_length = int(ahex(_data[5:7]), 16)
        # Record the number of peers in the data structure... we'll use it later (11 bytes per peer entry)
        self._local['NUM_PEERS'] = _peer_list_length/11
        self._logger.info('(%s) Peer List Received from Master: %s peers in this IPSC', self._system, self._local['NUM_PEERS'])
    
        # Iterate each peer entry in the peer list. Skip the header, then pull the next peer, the next, etc.
        for i in range(7, _peer_list_length +7, 11):
            # Extract various elements from each entry...
            _hex_radio_id = (_data[i:i+4])
            _hex_address  = (_data[i+4:i+8])
            _ip_address   = IPAddr(_hex_address)
            _hex_port     = (_data[i+8:i+10])
            _port         = int(ahex(_hex_port), 16)
            _hex_mode     = (_data[i+10:i+11])
     
            # Add this peer to a temporary PeerID list - used to remove any old peers no longer with us
            _temp_peers.append(_hex_radio_id)
        
            # This is done elsewhere for the master too, so we use a separate function
            _decoded_mode = process_mode_byte(_hex_mode)

            # If this entry WAS already in our list, update everything except the stats
            # in case this was a re-registration with a different mode, flags, etc.
            if _hex_radio_id in self._peers.keys():
                self._peers[_hex_radio_id]['IP'] = _ip_address
                self._peers[_hex_radio_id]['PORT'] = _port
                self._peers[_hex_radio_id]['MODE'] = _hex_mode
                self._peers[_hex_radio_id]['MODE_DECODE'] = _decoded_mode
                self._peers[_hex_radio_id]['FLAGS'] = ''
                self._peers[_hex_radio_id]['FLAGS_DECODE'] = ''
                self._logger.debug('(%s) Peer Updated: %s', self._system, self._peers[_hex_radio_id])

            # If this entry was NOT already in our list, add it.
            if _hex_radio_id not in self._peers.keys():
                self._peers[_hex_radio_id] = {
                    'IP':          _ip_address, 
                    'PORT':        _port, 
                    'MODE':        _hex_mode,            
                    'MODE_DECODE': _decoded_mode,
                    'FLAGS': '',
                    'FLAGS_DECODE': '',
                    'STATUS': {
                        'CONNECTED':               False,
                        'KEEP_ALIVES_SENT':        0,
                        'KEEP_ALIVES_MISSED':      0,
                        'KEEP_ALIVES_OUTSTANDING': 0,
                        'KEEP_ALIVES_RECEIVED':    0,
                        'KEEP_ALIVE_RX_TIME':      0
                        }
                    }
                self._logger.debug('(%s) Peer Added: %s', self._system, self._peers[_hex_radio_id])
    
        # Finally, check to see if there's a peer already in our list that was not in this peer list
        # and if so, delete it.
        for peer in self._peers.keys():
            if peer not in _temp_peers:
                self.de_register_peer(peer)
                self._logger.warning('(%s) Peer Deleted (not in new peer list): %s', self._system, int_id(peer))


    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    
    # If RCM reporting and reporting is network-based in the global configuration, 
    # send the RCM packet to the monitoring server
    def call_mon_status(self, _data):
        self._logger.debug('(%s) Repeater Call Monitor Origin Packet Received: %s', self._system, ahex(_data))
        if self._rcm:
            self._report.send_rcm(self._system + ','+ _data)
            
    def call_mon_rpt(self, _data):
        self._logger.debug('(%s) Repeater Call Monitor Repeating Packet Received: %s', self._system, ahex(_data))
        if self._rcm:
            self._report.send_rcm(self._system + ',' + _data)
            
    def call_mon_nack(self, _data):
        self._logger.debug('(%s) Repeater Call Monitor NACK Packet Received: %s', self._system, ahex(_data))
        if self._rcm:
            self._report.send_rcm(self._system + ',' + _data)
    
    def xcmp_xnl(self, _data):
        self._logger.debug('(%s) XCMP/XNL Packet Received: %s', self._system, ahex(_data))
        
    def repeater_wake_up(self, _data):
        self._logger.debug('(%s) Repeater Wake-Up Packet Received: %s', self._system, ahex(_data))
        
    def group_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        self._logger.debug('(%s) Group Voice Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))
    
    def private_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        self._logger.debug('(%s) Private Voice Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))
    
    def group_data(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        self._logger.debug('(%s) Group Data Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))
    
    def private_data(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        self._logger.debug('(%s) Private Data Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))

    def unknown_message(self, _packettype, _peerid, _data):
        self._logger.error('(%s) Unknown Message - Type: %s From: %s Packet: %s', self._system, ahex(_packettype), int_id(_peerid), ahex(_data))


    #************************************************
    #     IPSC SPECIFIC MAINTENANCE FUNCTIONS
    #************************************************
    
    # Simple function to send packets - handy to have it all in one place for debugging
    #
    def send_packet(self, _packet, (_host, _port)):
        if self._local['AUTH_ENABLED']:
            _hash = bhex((hmac_new(self._local['AUTH_KEY'],_packet,sha1)).hexdigest()[:20])
            _packet = _packet + _hash
        self.transport.write(_packet, (_host, _port))
        # USE THE FOLLOWING ONLY UNDER DIRE CIRCUMSTANCES -- PERFORMANCE IS ADVERSLY AFFECTED!
        #self._logger.debug('(%s) TX Packet to %s on port %s: %s', self._system, _host, _port, ahex(_packet))
        
    # Accept a complete packet, ready to be sent, and send it to all active peers + master in an IPSC
    #
    def send_to_ipsc(self, _packet):
        if self._local['AUTH_ENABLED']:
            _hash = bhex((hmac_new(self._local['AUTH_KEY'],_packet,sha1)).hexdigest()[:20])
            _packet = _packet + _hash
        # Send to the Master
        if self._master['STATUS']['CONNECTED']:
            self.transport.write(_packet, (self._master['IP'], self._master['PORT']))
        # Send to each connected Peer
        for peer in self._peers.keys():
            if self._peers[peer]['STATUS']['CONNECTED']:
                self.transport.write(_packet, (self._peers[peer]['IP'], self._peers[peer]['PORT']))
        
    
    # FUNTIONS FOR IPSC MAINTENANCE ACTIVITIES WE RESPOND TO
    
    # SOMEONE HAS SENT US A KEEP ALIVE - WE MUST ANSWER IT
    def peer_alive_req(self, _data, _peerid, _host, _port):
        _hex_mode      = (_data[5])
        _hex_flags     = (_data[6:10])
        _decoded_mode  = process_mode_byte(_hex_mode)
        _decoded_flags = process_flags_bytes(_hex_flags)
    
        self._peers[_peerid]['MODE'] = _hex_mode
        self._peers[_peerid]['MODE_DECODE'] = _decoded_mode
        self._peers[_peerid]['FLAGS'] = _hex_flags
        self._peers[_peerid]['FLAGS_DECODE'] = _decoded_flags
        self.send_packet(self.PEER_ALIVE_REPLY_PKT, (_host, _port))
        self.reset_keep_alive(_peerid)  # Might as well reset our own counter, we know it's out there...
        self._logger.debug('(%s) Keep-Alive reply sent to Peer %s, %s:%s', self._system, int_id(_peerid), _host, _port)

    # SOMEONE WANTS TO REGISTER WITH US - WE'RE COOL WITH THAT
    def peer_reg_req(self, _peerid, _host, _port):
        self.send_packet(self.PEER_REG_REPLY_PKT, (_host, _port))
        self._logger.info('(%s) Peer Registration Request From: %s, %s:%s', self._system, int_id(_peerid), _host, _port)


    # SOMEONE HAS ANSWERED OUR KEEP-ALIVE REQUEST - KEEP TRACK OF IT
    def peer_alive_reply(self, _peerid):
        self.reset_keep_alive(_peerid)
        self._peers[_peerid]['STATUS']['KEEP_ALIVES_RECEIVED'] += 1
        self._peers[_peerid]['STATUS']['KEEP_ALIVE_RX_TIME'] = int(time())
        self._logger.debug('(%s) Keep-Alive Reply (we sent the request) Received from Peer %s, %s:%s', self._system, int_id(_peerid), self._peers[_peerid]['IP'], self._peers[_peerid]['PORT'])
    
    # SOMEONE HAS ANSWERED OUR REQEST TO REGISTER WITH THEM - KEEP TRACK OF IT
    def peer_reg_reply(self, _peerid):
        if _peerid in self._peers.keys():
            self._peers[_peerid]['STATUS']['CONNECTED'] = True
            self._logger.info('(%s) Registration Reply From: %s, %s:%s', self._system, int_id(_peerid), self._peers[_peerid]['IP'], self._peers[_peerid]['PORT'])

    # OUR MASTER HAS ANSWERED OUR KEEP-ALIVE REQUEST - KEEP TRACK OF IT
    def master_alive_reply(self, _peerid):
        self.reset_keep_alive(_peerid)
        self._master['STATUS']['KEEP_ALIVES_RECEIVED'] += 1
        self._master['STATUS']['KEEP_ALIVE_RX_TIME'] = int(time())
        self._logger.debug('(%s) Keep-Alive Reply (we sent the request) Received from the Master %s, %s:%s', self._system, int_id(_peerid), self._master['IP'], self._master['PORT'])
    
    # OUR MASTER HAS SENT US A PEER LIST - PROCESS IT
    def peer_list_reply(self, _data, _peerid):
        self._master['STATUS']['PEER_LIST'] = True
        if len(_data) > 18:
            self.process_peer_list(_data)
        self._logger.debug('(%s) Peer List Reply Received From Master %s, %s:%s', self._system, int_id(_peerid), self._master['IP'], self._master['PORT'])
    
    # OUR MASTER HAS ANSWERED OUR REQUEST TO REGISTER - LOTS OF INFORMATION TO TRACK
    def master_reg_reply(self, _data, _peerid):
        _hex_mode      = _data[5]
        _hex_flags     = _data[6:10]
        _num_peers     = _data[10:12]
        _decoded_mode  = process_mode_byte(_hex_mode)
        _decoded_flags = process_flags_bytes(_hex_flags)
        
        self._local['NUM_PEERS'] = int(ahex(_num_peers), 16)
        self._master['RADIO_ID'] = _peerid
        self._master['MODE'] = _hex_mode
        self._master['MODE_DECODE'] = _decoded_mode
        self._master['FLAGS'] = _hex_flags
        self._master['FLAGS_DECODE'] = _decoded_flags
        self._master_stat['CONNECTED'] = True
        self._master_stat['KEEP_ALIVES_OUTSTANDING'] = 0
        self._logger.warning('(%s) Registration response (we requested reg) from the Master: %s, %s:%s (%s peers)', self._system, int_id(_peerid), self._master['IP'], self._master['PORT'], self._local['NUM_PEERS'])
    
    # WE ARE MASTER AND SOMEONE HAS REQUESTED REGISTRATION FROM US - ANSWER IT
    def master_reg_req(self, _data, _peerid, _host, _port):
        _ip_address    = _host
        _port          = _port
        _hex_mode      = _data[5]
        _hex_flags     = _data[6:10]
        _decoded_mode  = process_mode_byte(_hex_mode)
        _decoded_flags = process_flags_bytes(_hex_flags)
        
        self.MASTER_REG_REPLY_PKT = (MASTER_REG_REPLY + self._local_id + self.TS_FLAGS + hex_str_2(self._local['NUM_PEERS']) + IPSC_VER)
        self.send_packet(self.MASTER_REG_REPLY_PKT, (_host, _port))
        self._logger.info('(%s) Master Registration Packet Received from peer %s, %s:%s', self._system, int_id(_peerid), _host, _port)

        # If this entry was NOT already in our list, add it.
        if _peerid not in self._peers.keys():
            self._peers[_peerid] = {
                'IP':          _ip_address, 
                'PORT':        _port, 
                'MODE':        _hex_mode,            
                'MODE_DECODE': _decoded_mode,
                'FLAGS':       _hex_flags,
                'FLAGS_DECODE': _decoded_flags,
                'STATUS': {
                    'CONNECTED':               True,
                    'KEEP_ALIVES_SENT':        0,
                    'KEEP_ALIVES_MISSED':      0,
                    'KEEP_ALIVES_OUTSTANDING': 0,
                    'KEEP_ALIVES_RECEIVED':    0,
                    'KEEP_ALIVE_RX_TIME':      int(time())
                    }
                }
        self._local['NUM_PEERS'] = len(self._peers)       
        self._logger.debug('(%s) Peer Added To Peer List: %s, %s:%s (IPSC now has %s Peers)', self._system, self._peers[_peerid], _host, _port, self._local['NUM_PEERS'])
    
    # WE ARE MASTER AND SOEMONE SENT US A KEEP-ALIVE - ANSWER IT, TRACK IT
    def master_alive_req(self, _peerid, _host, _port):
        if _peerid in self._peers.keys():
            self._peers[_peerid]['STATUS']['KEEP_ALIVES_RECEIVED'] += 1
            self._peers[_peerid]['STATUS']['KEEP_ALIVE_RX_TIME'] = int(time())
            self.send_packet(self.MASTER_ALIVE_REPLY_PKT, (_host, _port))
            self._logger.debug('(%s) Master Keep-Alive Request Received from peer %s, %s:%s', self._system, int_id(_peerid), _host, _port)
        else:
            self._logger.warning('(%s) Master Keep-Alive Request Received from *UNREGISTERED* peer %s, %s:%s', self._system, int_id(_peerid), _host, _port)
    
    # WE ARE MASTER AND A PEER HAS REQUESTED A PEER LIST - SEND THEM ONE
    def peer_list_req(self, _peerid):
        if _peerid in self._peers.keys():
            self._logger.debug('(%s) Peer List Request from peer %s', self._system, int_id(_peerid))
            self.send_to_ipsc(self.PEER_LIST_REPLY_PKT + build_peer_list(self._peers))
        else:
            self._logger.warning('(%s) Peer List Request Received from *UNREGISTERED* peer %s', self._system, int_id(_peerid))

    
    # Reset the outstanding keep-alive counter for _peerid...
    # Used when receiving acks OR when we see traffic from a repeater, since they ignore keep-alives when transmitting
    #
    def reset_keep_alive(self, _peerid):
        if _peerid in self._peers.keys():
            self._peers[_peerid]['STATUS']['KEEP_ALIVES_OUTSTANDING'] = 0
            self._peers[_peerid]['STATUS']['KEEP_ALIVE_RX_TIME'] = int(time())
        if _peerid == self._master['RADIO_ID']:
            self._master_stat['KEEP_ALIVES_OUTSTANDING'] = 0


    # THE NEXT SECTION DEFINES FUNCTIONS THAT MUST BE DIFFERENT FOR HASHED AND UNHASHED PACKETS
    # HASHED MEANS AUTHENTICATED IPSC
    # UNHASHED MEANS UNAUTHENTICATED IPSC

    # NEXT THREE FUNCITONS ARE FOR AUTHENTICATED PACKETS
    
    # Take a packet to be SENT, calculate auth hash and return the whole thing
    #
    def hashed_packet(self, _key, _data):
        _hash = bhex((hmac_new(_key,_data,sha1)).hexdigest()[:20])
        return _data + _hash
    
    # Remove the hash from a packet and return the payload
    #
    def strip_hash(self, _data):
        return _data[:-10]
    
    # Take a RECEIVED packet, calculate the auth hash and verify authenticity
    #
    def validate_auth(self, _key, _data):
        _payload = self.strip_hash(_data)
        _hash = _data[-10:]
        _chk_hash = bhex((hmac_new(_key,_payload,sha1)).hexdigest()[:20])   

        if _chk_hash == _hash:
            return True
        else:
            return False


    #************************************************
    #     TIMED LOOP - CONNECTION MAINTENANCE
    #************************************************

    # Timed loop initialization (called by the twisted reactor)
    #       
    def startProtocol(self):
        # Timed loops for:
        #   IPSC connection establishment and maintenance
        #   Reporting/Housekeeping
        #
        # IF WE'RE NOT THE MASTER...
        if not self._local['MASTER_PEER']:
            self._peer_maintenance = task.LoopingCall(self.peer_maintenance_loop)
            self._peer_maintenance_loop = self._peer_maintenance.start(self._local['ALIVE_TIMER'])
        #
        # IF WE ARE THE MASTER...
        if self._local['MASTER_PEER']:
            self._master_maintenance = task.LoopingCall(self.master_maintenance_loop)
            self._master_maintenance_loop = self._master_maintenance.start(self._local['ALIVE_TIMER'])

    
    # Timed loop used for IPSC connection Maintenance when we are the MASTER
    #    
    def master_maintenance_loop(self):
        self._logger.debug('(%s) MASTER Connection Maintenance Loop Started', self._system)
        update_time = int(time())
        
        for peer in self._peers.keys():
            keep_alive_delta = update_time - self._peers[peer]['STATUS']['KEEP_ALIVE_RX_TIME']
            self._logger.debug('(%s) Time Since Last KeepAlive Request from Peer %s: %s seconds', self._system, int_id(peer), keep_alive_delta)
          
            if keep_alive_delta > 120:
                self.de_register_peer(peer)
                self.send_to_ipsc(self.PEER_LIST_REPLY_PKT + build_peer_list(self._peers))
                self._logger.warning('(%s) Timeout Exceeded for Peer %s, De-registering', self._system, int_id(peer))
    
    # Timed loop used for IPSC connection Maintenance when we are a PEER
    #
    def peer_maintenance_loop(self):
        self._logger.debug('(%s) PEER Connection Maintenance Loop Started', self._system)

        # If the master isn't connected, we have to do that before we can do anything else!
        #
        if not self._master_stat['CONNECTED']:
            self.send_packet(self.MASTER_REG_REQ_PKT, self._master_sock)
            self._logger.info('(%s) Registering with the Master: %s:%s', self._system, self._master['IP'], self._master['PORT'])
        
        # Once the master is connected, we have to send keep-alives.. and make sure we get them back
        elif self._master_stat['CONNECTED']:
            # Send keep-alive to the master
            self.send_packet(self.MASTER_ALIVE_PKT, self._master_sock)
            self._logger.debug('(%s) Keep Alive Sent to the Master: %s, %s:%s', self._system, int_id(self._master['RADIO_ID']) ,self._master['IP'], self._master['PORT'])
            
            # If we had a keep-alive outstanding by the time we send another, mark it missed.
            if (self._master_stat['KEEP_ALIVES_OUTSTANDING']) > 0:
                self._master_stat['KEEP_ALIVES_MISSED'] += 1
                self._logger.info('(%s) Master Keep-Alive Missed: %s:%s', self._system, self._master['IP'], self._master['PORT'])
            
            # If we have missed too many keep-alives, de-register the master and start over.
            if self._master_stat['KEEP_ALIVES_OUTSTANDING'] >= self._local['MAX_MISSED']:
                self._master_stat['CONNECTED'] = False
                self._master_stat['KEEP_ALIVES_OUTSTANDING'] = 0
                self._logger.error('(%s) Maximum Master Keep-Alives Missed -- De-registering the Master: %s:%s', self._system, self._master['IP'], self._master['PORT'])
            
            # Update our stats before we move on...
            self._master_stat['KEEP_ALIVES_SENT'] += 1
            self._master_stat['KEEP_ALIVES_OUTSTANDING'] += 1
            
        else:
            # This is bad. If we get this message, we need to reset the state and try again
            self._logger.error('->> (%s) Master in UNKOWN STATE: %s:%s', self._system, self._master_sock)
            self._master_stat['CONNECTED'] = False
        
        
        # If the master is connected and we don't have a peer-list yet....
        #
        if (self._master_stat['CONNECTED'] == True) and (self._master_stat['PEER_LIST'] == False):
            # Ask the master for a peer-list
            if self._local['NUM_PEERS']:
                self.send_packet(self.PEER_LIST_REQ_PKT, self._master_sock)
                self._logger.info('(%s), No Peer List - Requesting One From the Master', self._system)
            else:
                self._master_stat['PEER_LIST'] = True
                self._logger.debug('(%s), Skip asking for a Peer List, we are the only Peer', self._system)


        # If we do have a peer-list, we need to register with the peers and send keep-alives...
        #
        if self._master_stat['PEER_LIST']:
            # Iterate the list of peers... so we do this for each one.
            for peer in self._peers.keys():

                # We will show up in the peer list, but shouldn't try to talk to ourselves.
                if peer == self._local_id:
                    continue

                # If we haven't registered to a peer, send a registration
                if not self._peers[peer]['STATUS']['CONNECTED']:
                    self.send_packet(self.PEER_REG_REQ_PKT, (self._peers[peer]['IP'], self._peers[peer]['PORT']))
                    self._logger.info('(%s) Registering with Peer %s, %s:%s', self._system, int_id(peer), self._peers[peer]['IP'], self._peers[peer]['PORT'])

                # If we have registered with the peer, then send a keep-alive
                elif self._peers[peer]['STATUS']['CONNECTED']:
                    self.send_packet(self.PEER_ALIVE_REQ_PKT, (self._peers[peer]['IP'], self._peers[peer]['PORT']))
                    self._logger.debug('(%s) Keep-Alive Sent to the Peer %s, %s:%s', self._system, int_id(peer), self._peers[peer]['IP'], self._peers[peer]['PORT'])

                    # If we have a keep-alive outstanding by the time we send another, mark it missed.
                    if self._peers[peer]['STATUS']['KEEP_ALIVES_OUTSTANDING'] > 0:
                        self._peers[peer]['STATUS']['KEEP_ALIVES_MISSED'] += 1
                        self._logger.info('(%s) Peer Keep-Alive Missed for %s, %s:%s', self._system, int_id(peer), self._peers[peer]['IP'], self._peers[peer]['PORT'])

                    # If we have missed too many keep-alives, de-register the peer and start over.
                    if self._peers[peer]['STATUS']['KEEP_ALIVES_OUTSTANDING'] >= self._local['MAX_MISSED']:
                        self._peers[peer]['STATUS']['CONNECTED'] = False
                        #del peer   # Becuase once it's out of the dictionary, you can't use it for anything else.
                        self._logger.warning('(%s) Maximum Peer Keep-Alives Missed -- De-registering the Peer: %s, %s:%s', self._system, int_id(peer), self._peers[peer]['IP'], self._peers[peer]['PORT'])
                    
                    # Update our stats before moving on...
                    self._peers[peer]['STATUS']['KEEP_ALIVES_SENT'] += 1
                    self._peers[peer]['STATUS']['KEEP_ALIVES_OUTSTANDING'] += 1
    


    #************************************************
    #     MESSAGE RECEIVED - TAKE ACTION
    #************************************************

    # Actions for received packets by type: For every packet received, there are some things that we need to do:
    #   Decode some of the info
    #   Check for auth and authenticate the packet
    #   Strip the hash from the end... we don't need it anymore
    #
    # Once they're done, we move on to the processing or callbacks for each packet type.
    #
    # Callbacks are iterated in the order of "more likely" to "less likely" to reduce processing time
    #
    def datagramReceived(self, data, (host, port)):
        _packettype = data[0:1]
        _peerid     = data[1:5]
        _ipsc_seq   = data[5:6]
    
        # AUTHENTICATE THE PACKET
        if self._local['AUTH_ENABLED']:
            if not self.validate_auth(self._local['AUTH_KEY'], data):
                self._logger.warning('(%s) AuthError: IPSC packet failed authentication. Type %s: Peer: %s, %s:%s', self._system, ahex(_packettype), int_id(_peerid), host, port)
                return
            
            # REMOVE SHA-1 AUTHENTICATION HASH: WE NO LONGER NEED IT
            else:
                data = self.strip_hash(data)

        # PACKETS THAT WE RECEIVE FROM ANY VALID PEER OR VALID MASTER
        if _packettype in ANY_PEER_REQUIRED:
            if not(self.valid_master(_peerid) == False or self.valid_peer(_peerid) == False):
                self._logger.warning('(%s) PeerError: Peer not in peer-list: %s, %s:%s', self._system, int_id(_peerid), host, port)
                return
                
            # ORIGINATED BY SUBSCRIBER UNITS - a.k.a someone transmitted
            if _packettype in USER_PACKETS:
                # Extract IPSC header not already extracted
                _src_sub    = data[6:9]
                _dst_sub    = data[9:12]
                _call_type  = data[12:13]
                _unknown_1  = data[13:17]
                _call_info  = int_id(data[17:18])                
                _ts         = bool(_call_info & TS_CALL_MSK) + 1
                _end        = bool(_call_info & END_MSK)
                
                # Extract RTP Header Fields
                '''
                Coming soon kids!!!
                Looks like version, padding, extention, CSIC, payload type and SSID never change.
                The things we might care about are below.
                _rtp_byte_1 = int_id(data[18:19])
                _rtp_byte_2 = int_id(data[19:20])
                _rtp_seq    = int_id(data[20:22])
                _rtp_tmstmp = int_id(data[22:26])
                _rtp_ssid = int_id(data[26:30])
                
                # Extract RTP Payload Data Fields
                _payload_type = int_id(data[30:31])
                '''

                # User Voice and Data Call Types:
                if _packettype == GROUP_VOICE:
                    self.reset_keep_alive(_peerid)
                    self.group_voice(_src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
            
                elif _packettype == PVT_VOICE:
                    self.reset_keep_alive(_peerid)
                    self.private_voice(_src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
                    
                elif _packettype == GROUP_DATA:
                    self.reset_keep_alive(_peerid)
                    self.group_data(_src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
                    
                elif _packettype == PVT_DATA:
                    self.reset_keep_alive(_peerid)
                    self.private_data(_src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
                return


            # MOTOROLA XCMP/XNL CONTROL PROTOCOL: We don't process these (yet)   
            elif _packettype == XCMP_XNL:
                self.xcmp_xnl(data)
                return


            # ORIGINATED BY PEERS, NOT IPSC MAINTENANCE: Call monitoring is all we've found here so far 
            elif _packettype == CALL_MON_STATUS:
                self.call_mon_status(data)
                return
                
            elif _packettype == CALL_MON_RPT:
                self.call_mon_rpt(data)
                return
                
            elif _packettype == CALL_MON_NACK:
                self.call_mon_nack(data)
                return
            
            
            # IPSC CONNECTION MAINTENANCE MESSAGES
            elif _packettype == DE_REG_REQ:
                self.de_register_peer(_peerid)
                self._logger.warning('(%s) Peer De-Registration Request From: %s, %s:%s', self._system, int_id(_peerid), host, port)
                return
            
            elif _packettype == DE_REG_REPLY:
                self._logger.warning('(%s) Peer De-Registration Reply From: %s, %s:%s', self._system, int_id(_peerid), host, port)
                return
                
            elif _packettype == RPT_WAKE_UP:
                self.repeater_wake_up(data)
                self._logger.debug('(%s) Repeater Wake-Up Packet From: %s, %s:%s', self._system, int_id(_peerid), host, port)
                return
            return


        # THE FOLLOWING PACKETS ARE RECEIVED ONLY IF WE ARE OPERATING AS A PEER
        
        # ONLY ACCEPT FROM A PREVIOUSLY VALIDATED PEER
        if _packettype in PEER_REQUIRED:
            if not self.valid_peer(_peerid):
                self._logger.warning('(%s) PeerError: Peer not in peer-list: %s, %s:%s', self._system, int_id(_peerid), host, port)
                return
            
            # REQUESTS FROM PEERS: WE MUST REPLY IMMEDIATELY FOR IPSC MAINTENANCE
            if _packettype == PEER_ALIVE_REQ:
                self.peer_alive_req(data, _peerid, host, port)
                return
                                
            elif _packettype == PEER_REG_REQ:
                self.peer_reg_req(_peerid, host, port)
                return
                
            # ANSWERS FROM REQUESTS WE SENT TO PEERS: WE DO NOT REPLY
            elif _packettype == PEER_ALIVE_REPLY:
                self.peer_alive_reply(_peerid)
                return                

            elif _packettype == PEER_REG_REPLY:
                self.peer_reg_reply(_peerid)
                return
            return
            
        
        # PACKETS ONLY ACCEPTED FROM OUR MASTER

        # PACKETS WE ONLY ACCEPT IF WE HAVE FINISHED REGISTERING WITH OUR MASTER
        if _packettype in MASTER_REQUIRED:
            if not self.valid_master(_peerid):
                self._logger.warning('(%s) MasterError: %s, %s:%s is not the master peer', self._system, int_id(_peerid), host, port)
                return
            
            # ANSWERS FROM REQUESTS WE SENT TO THE MASTER: WE DO NOT REPLY    
            if _packettype == MASTER_ALIVE_REPLY:
                self.master_alive_reply(_peerid)
                return
            
            elif _packettype == PEER_LIST_REPLY:
                self.peer_list_reply(data, _peerid)
                return
            return
            
        # THIS MEANS WE HAVE SUCCESSFULLY REGISTERED TO OUR MASTER - RECORD MASTER INFORMATION
        elif _packettype == MASTER_REG_REPLY:
            self.master_reg_reply(data, _peerid)
            return
        
        
        # THE FOLLOWING PACKETS ARE RECEIVED ONLLY IF WE ARE OPERATING AS A MASTER
        # REQUESTS FROM PEERS: WE MUST REPLY IMMEDIATELY FOR IPSC MAINTENANCE
        
        # REQUEST TO REGISTER TO THE IPSC
        elif _packettype == MASTER_REG_REQ:
            self.master_reg_req(data, _peerid, host, port)           
            return
          
        # REQUEST FOR A KEEP-ALIVE REPLY (WE KNOW THE PEER IS STILL ALIVE TOO) 
        elif _packettype == MASTER_ALIVE_REQ:
            self.master_alive_req(_peerid, host, port)
            return
            
        # REQUEST FOR A PEER LIST
        elif _packettype == PEER_LIST_REQ:
            self.peer_list_req(_peerid)
            return

        # PACKET IS OF AN UNKNOWN TYPE. LOG IT AND IDENTTIFY IT!
        else:
            self.unknown_message(_packettype, _peerid, data)
            return


#
# Socket-based reporting section
#
class report(NetstringReceiver):
    def __init__(self, factory):
        self._factory = factory

    def connectionMade(self):
        self._factory.clients.append(self)
        self._factory._logger.info('DMRlink reporting client connected: %s', self.transport.getPeer())

    def connectionLost(self, reason):
        self._factory._logger.info('DMRlink reporting client disconnected: %s', self.transport.getPeer())
        self._factory.clients.remove(self)

    def stringReceived(self, data):
        self.process_message(data)

    def process_message(self, _message):
        opcode = _message[:1]
        if opcode == REPORT_OPCODES['CONFIG_REQ']:
            self._factory._logger.info('DMRlink reporting client sent \'CONFIG_REQ\': %s', self.transport.getPeer())
            self.send_config()
        else:
            print('got unknown opcode')
        
class reportFactory(Factory):
    def __init__(self, config, logger):
        self._config = config
        self._logger = logger
        
    def buildProtocol(self, addr):
        if (addr.host) in self._config['REPORTS']['REPORT_CLIENTS'] or '*' in self._config['REPORTS']['REPORT_CLIENTS']:
            self._logger.debug('Permitting report server connection attempt from: %s:%s', addr.host, addr.port)
            return report(self)
        else:
            self._logger.error('Invalid report server connection attempt from: %s:%s', addr.host, addr.port)
            return None
            
    def send_clients(self, _message):
        for client in self.clients:
            client.sendString(_message)
            
    def send_config(self):
        serialized = pickle.dumps(self._config['SYSTEMS'], protocol=pickle.HIGHEST_PROTOCOL)
        self.send_clients(REPORT_OPCODES['CONFIG_SND']+serialized)
        
    def send_rcm(self, _data):
        self.send_clients(REPORT_OPCODES['RCM_SND']+_data)


#************************************************
#      MAIN PROGRAM LOOP STARTS HERE
#************************************************

if __name__ == '__main__':
    import argparse
    import sys
    import os
    import signal
    
    from ipsc.dmrlink_config import build_config
    from ipsc.dmrlink_log import config_logging
    
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
    logger.info('DMRlink \'dmrlink.py\' (c) 2013 - 2017 N0MJS & the K0USY Group - SYSTEM STARTING...')
    
    # Set signal handers so that we can gracefully exit if need be
    def sig_handler(_signal, _frame):
        logger.info('*** DMRLINK IS TERMINATING WITH SIGNAL %s ***', str(_signal))
        for system in systems:
            systems[system].de_register_self()
        reactor.stop()
    
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
        signal.signal(sig, sig_handler)
    
    # INITIALIZE THE REPORTING LOOP
    report_server = config_reports(CONFIG, logger, reportFactory)
    
    # Build ID Aliases
    peer_ids, subscriber_ids, talkgroup_ids, local_ids = build_aliases(CONFIG, logger)
        
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGRUED IPSC
    systems = mk_ipsc_systems(CONFIG, logger, systems, IPSC, report_server)



    # INITIALIZATION COMPLETE -- START THE REACTOR
    reactor.run()
