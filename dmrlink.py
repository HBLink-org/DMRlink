#!/usr/bin/env python
# Copyright (c) 2013 Cortney T. Buffington, N0MJS and the K0USY Group. n0mjs@me.com
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

from __future__ import print_function
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h
import ConfigParser
import os
import sys
import argparse
import binascii
import hmac
import hashlib
import socket
import csv

#************************************************
#     IMPORTING OTHER FILES - '#include'
#************************************************

# Import system logger configuration
#
try:
    from ipsc.ipsc_logger import logger
except ImportError:
    sys.exit('System logger configuration not found or invalid')

# Import IPSC message types and version information
#
try:
    from ipsc.ipsc_message_types import *
except ImportError:
    sys.exit('IPSC message types file not found or invalid')

# Import IPSC flag mask values
#
try:
    from ipsc.ipsc_mask import *
except ImportError:
    sys.exit('IPSC mask values file not found or invalid')

# Import the Alias files for numeric ids. This is split to save
# time making lookukps in one huge dictionary
#
subscriber_ids = {}
peer_ids = {}
talkgroup_ids = {}

try:
    with open('./subscriber_ids.csv', 'rU') as subscriber_ids_csv:
        subscribers = csv.reader(subscriber_ids_csv, dialect='excel', delimiter=',')
        for row in subscribers:
            subscriber_ids[int(row[1])] = (row[0])
except ImportError:
    logger.warning('subscriber_ids.csv not found: Subscriber aliases will not be avaiale')
    
try:
    with open('./peer_ids.csv', 'rU') as peer_ids_csv:
        peers = csv.reader(peer_ids_csv, dialect='excel', delimiter=',')
        for row in peers:
            peer_ids[int(row[1])] = (row[0])
except ImportError:
    logger.warning('peer_ids.csv not found: Peer aliases will not be avaiale')

try:
    with open('./talkgroup_ids.csv', 'rU') as talkgroup_ids_csv:
        talkgroups = csv.reader(talkgroup_ids_csv, dialect='excel', delimiter=',')
        for row in talkgroups:
            talkgroup_ids[int(row[1])] = (row[0])
except ImportError:
    logger.warning('talkgroup_ids.csv not found: Talkgroup aliases will not be avaiale')

    
#************************************************
#     PARSE THE CONFIG FILE AND BUILD STRUCTURE
#************************************************

networks = {}
NETWORK = {}

config = ConfigParser.ConfigParser()
config.read('./dmrlink.cfg')

try:
    for section in config.sections():
        if section == 'GLOBAL':
            pass
        else:
            NETWORK.update({section: {'LOCAL': {}, 'MASTER': {}, 'PEERS': {}}})
            NETWORK[section]['LOCAL'].update({
                'MODE': '',
                'PEER_OPER': True,
                'PEER_MODE': 'DIGITAL',
                'FLAGS': '',
                'MAX_MISSED': 10,
                'NUM_PEERS': 0,
                'STATUS': {
                    'ACTIVE': False
                    },
                'ENABLED': config.getboolean(section, 'ENABLED'),
                'TS1_LINK': config.getboolean(section, 'TS1_LINK'),
                'TS2_LINK': config.getboolean(section, 'TS2_LINK'),
                'AUTH_ENABLED': config.getboolean(section, 'AUTH_ENABLED'),
                'RADIO_ID': hex(int(config.get(section, 'RADIO_ID')))[2:].rjust(8,'0').decode('hex'),
                'PORT': config.getint(section, 'PORT'),
                'ALIVE_TIMER': config.getint(section, 'ALIVE_TIMER'),
                'AUTH_KEY': (config.get(section, 'AUTH_KEY').rjust(40,'0')).decode('hex'),
                })
            NETWORK[section]['MASTER'].update({
                'RADIO_ID': '\x00\x00\x00\x00',
                'MODE': '\x00',
                'PEER_OPER': False,
                'PEER_MODE': '',
                'TS1_LINK': False,
                'TS2_LINK': False,
                'FLAGS': '\x00\x00\x00\x00',
                'STATUS': {
                    'CONNECTED': False,
                    'PEER_LIST': False,
                    'KEEP_ALIVES_SENT': 0,
                    'KEEP_ALIVES_MISSED': 0,
                    'KEEP_ALIVES_OUTSTANDING': 0 
                    },
                'IP': config.get(section, 'MASTER_IP'),
                'PORT': config.getint(section, 'MASTER_PORT')
                })
        
            if NETWORK[section]['LOCAL']['AUTH_ENABLED']:
                #0x60 - 3rd Party App & Repeater Monitoring, 0x1C - Voice and Data calls only, 0xDC - Voice, Data and XCMP/XNL
                NETWORK[section]['LOCAL']['FLAGS'] = '\x00\x00\x60\x1C'
                #NETWORK[section]['LOCAL']['FLAGS'] = '\x00\x00\x60\xDC'
            else:
                NETWORK[section]['LOCAL']['FLAGS'] = '\x00\x00\x60\x0C'
    
            if not NETWORK[section]['LOCAL']['TS1_LINK'] and not NETWORK[section]['LOCAL']['TS2_LINK']:    
                NETWORK[section]['LOCAL']['MODE'] = '\x65'
            elif NETWORK[section]['LOCAL']['TS1_LINK'] and not NETWORK[section]['LOCAL']['TS2_LINK']:    
                NETWORK[section]['LOCAL']['MODE'] = '\x66'
            elif not NETWORK[section]['LOCAL']['TS1_LINK'] and NETWORK[section]['LOCAL']['TS2_LINK']:    
                NETWORK[section]['LOCAL']['MODE'] = '\x69'
            else:
                NETWORK[section]['LOCAL']['MODE'] = '\x6A'
except:
    logger.critical('Could not parse configuration file, exiting...')
    sys.exit('Could not parse configuration file, exiting...')

#************************************************
#     UTILITY FUNCTIONS FOR INTERNAL USE
#************************************************

# Convert a hex string to an int (radio ID, etc.)
#
def int_id(_hex_string):
    return int(h(_hex_string), 16)

# Re-Write Source Radio-ID (DMR NAT)
#
def dmr_nat(_data, _src_id, _nat_id):
    _data = _data.replace(_src_id, _nat_id)
    return _data

# Lookup text data for numeric IDs
#
def get_info(_id, _dict):
    if _id in _dict:
            return _dict[_id]
    return _id

# Determine if the provided peer ID is valid for the provided network 
#
def valid_peer(_peer_list, _peerid):
    if _peerid in _peer_list:
        return True        
    return False


# Determine if the provided master ID is valid for the provided network
#
def valid_master(_network, _peerid):
    if NETWORK[_network]['MASTER']['RADIO_ID'] == _peerid:
        return True     
    else:
        return False
        
            
# Accept a complete packet, ready to be sent, and send it to all active peers + master in an IPSC
#
def send_to_ipsc(_target, _packet):
    _network = NETWORK[_target]
    _network_instance = networks[_target]
    _peers = _network['PEERS']
    
    # Send to the Master
    _network_instance.transport.write(_packet, (_network['MASTER']['IP'], _network['MASTER']['PORT']))
    # Send to each connected Peer
    for peer in _peers.keys():
        if _peers[peer]['STATUS']['CONNECTED'] == True:
            _network_instance.transport.write(_packet, (_peers[peer]['IP'], _peers[peer]['PORT']))

    
# De-register a peer from an IPSC by removing it's infomation
#
def de_register_peer(_network, _peerid):
    # Iterate for the peer in our data
    if _peerid in self._peers.keys():
        del self._peers[_peerid]
        logger.info('(%s) Peer De-Registration Requested for: %s', _network, h(_peerid))
        return
    else:
        logger.warning('(%s) Peer De-Registration Requested for: %s, but we don\'t have a listing for this peer', _network, h(_peerid))
        pass
       
        
# Take a recieved peer list and the network it belongs to, process and populate the
# data structure in my_ipsc_config with the results, and return a simple list of peers.
#
def process_peer_list(_data, _network):
    # Determine the length of the peer list for the parsing iterator
    _peer_list_length = int(h(_data[5:7]), 16)
    # Record the number of peers in the data structure... we'll use it later (11 bytes per peer entry)
    NETWORK[_network]['LOCAL']['NUM_PEERS'] = _peer_list_length/11
    logger.info('(%s) Peer List Received from Master: %s peers in this IPSC', _network, _peer_list_length/11)
    
    # Iterate each peer entry in the peer list. Skip the header, then pull the next peer, the next, etc.
    for i in range(7, (_peer_list_length)+7, 11):
        # Extract various elements from each entry...
        _hex_radio_id = (_data[i:i+4])
        _hex_address  = (_data[i+4:i+8])
        _ip_address   = socket.inet_ntoa(_hex_address)
        _hex_port     = (_data[i+8:i+10])
        _port         = int(h(_hex_port), 16)
        _hex_mode     = (_data[i+10:i+11])
        _mode         = int(h(_hex_mode), 16)
        # mask individual Mode parameters
        _link_op      = _mode & PEER_OP_MSK
        _link_mode    = _mode & PEER_MODE_MSK
        _ts1          = _mode & IPSC_TS1_MSK
        _ts2          = _mode & IPSC_TS2_MSK    
        
        # Determine whether or not the peer is operational
        if   _link_op == 0b01000000:
            _peer_op = True
        else:
            _peer_op = False
              
        # Determine the operational mode of the peer
        if   _link_mode == 0b00000000:
            _peer_mode = 'NO_RADIO'
        elif _link_mode == 0b00010000:
            _peer_mode = 'ANALOG'
        elif _link_mode == 0b00100000:
            _peer_mode = 'DIGITAL'
        else:
            _peer_node = 'NO_RADIO'
            
        # Determine whether or not timeslot 1 is linked
        if _ts1 == 0b00001000:
             _ts1 = True
        else:
             _ts1 = False
             
        # Determine whether or not timeslot 2 is linked
        if _ts2 == 0b00000010:
            _ts2 = True
        else:
            _ts2 = False  

        # If this entry was NOT already in our list, add it.
        #     Note: We keep a "simple" peer list in addition to the large data
        #           structure because soemtimes, we just need to identify a
        #           peer quickly.
        if _hex_radio_id not in NETWORK[_network]['PEERS'].keys():
            NETWORK[_network]['PEERS'][_hex_radio_id] = {
                'IP':        _ip_address, 
                'PORT':      _port, 
                'MODE':      _hex_mode,
                'PEER_OPER': _peer_op,
                'PEER_MODE': _peer_mode,
                'TS1_LINK':  _ts1,
                'TS2_LINK':  _ts2,
                'STATUS': {
                    'CONNECTED': False,
                    'KEEP_ALIVES_SENT': 0,
                    'KEEP_ALIVES_MISSED': 0,
                    'KEEP_ALIVES_OUTSTANDING': 0
                    }
                }


# Gratuituous print-out of the peer list.. Pretty much debug stuff.
#
def print_peer_list(_network):
    _peers = NETWORK[_network]['PEERS']
    
    _status = NETWORK[_network]['MASTER']['STATUS']['PEER_LIST']
    #print('Peer List Status for {}: {}' .format(_network, _status))
    
    if _status and not NETWORK[_network]['PEERS']:
        print('We are the only peer for: %s' % _network)
        print('')
        return
             
    print('Peer List for: %s' % _network)
    for peer in _peers.keys():
        _this_peer = _peers[peer]
        _this_peer_stat = _this_peer['STATUS']
        
        if peer == NETWORK[_network]['LOCAL']['RADIO_ID']:
            me = '(self)'
        else:
            me = ''
              
        print('\tRADIO ID: {} {}' .format(int(h(peer), 16), me))
        print('\t\tIP Address: {}:{}' .format(_this_peer['IP'], _this_peer['PORT']))
        print('\t\tOperational: {},  Mode: {},  TS1 Link: {},  TS2 Link: {}' .format(_this_peer['PEER_OPER'], _this_peer['PEER_MODE'], _this_peer['TS1_LINK'], _this_peer['TS2_LINK']))
        print('\t\tStatus: {},  KeepAlives Sent: {},  KeepAlives Outstanding: {},  KeepAlives Missed: {}' .format(_this_peer_stat['CONNECTED'], _this_peer_stat['KEEP_ALIVES_SENT'], _this_peer_stat['KEEP_ALIVES_OUTSTANDING'], _this_peer_stat['KEEP_ALIVES_MISSED']))

    print('')
 
# Gratuituous print-out of Master info.. Pretty much debug stuff.
#
def print_master(_network):
    _master = NETWORK[_network]['MASTER']
    print('Master for %s' % _network)
    print('\tRADIO ID: {}' .format(int(h(_master['RADIO_ID']), 16)))
    print('\t\tIP Address: {}:{}' .format(_master['IP'], _master['PORT']))
    print('\t\tOperational: {},  Mode: {},  TS1 Link: {},  TS2 Link: {}' .format(_master['PEER_OPER'], _master['PEER_MODE'], _master['TS1_LINK'], _master['TS2_LINK']))
    print('\t\tStatus: {},  KeepAlives Sent: {},  KeepAlives Outstanding: {},  KeepAlives Missed: {}' .format(_master['STATUS']['CONNECTED'], _master['STATUS']['KEEP_ALIVES_SENT'], _master['STATUS']['KEEP_ALIVES_OUTSTANDING'], _master['STATUS']['KEEP_ALIVES_MISSED']))


#************************************************
#********                             ***********
#********    IPSC Network 'Engine'    ***********
#********                             ***********
#************************************************

#************************************************
#     Base Class (used nearly all of the time)
#************************************************


class IPSC(DatagramProtocol):
    
    # Modify the initializer to set up our environment and build the packets
    # we need to maitain connections
    #
    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            # Housekeeping: create references to the configuration and status data for this IPSC instance.
            # Some configuration objects that are used frequently and have lengthy names are shortened
            # such as (self._master_sock) expands to (self._config['MASTER']['IP'], self._config['MASTER']['PORT']).
            # Note that many of them reference each other... this is the Pythonic way.
            #
            self._network = args[0]
            self._config = NETWORK[self._network]
            #
            self._local = self._config['LOCAL']
            self._local_stat = self._local['STATUS']
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
            self.TS_FLAGS             = (self._local['MODE'] + self._local['FLAGS'])
            self.MASTER_REG_REQ_PKT   = (MASTER_REG_REQ + self._local_id + self.TS_FLAGS + IPSC_VER)
            self.MASTER_ALIVE_PKT     = (MASTER_ALIVE_REQ + self._local_id + self.TS_FLAGS + IPSC_VER)
            self.PEER_LIST_REQ_PKT    = (PEER_LIST_REQ + self._local_id)
            self.PEER_REG_REQ_PKT     = (PEER_REG_REQ + self._local_id + IPSC_VER)
            self.PEER_REG_REPLY_PKT   = (PEER_REG_REPLY + self._local_id + IPSC_VER)
            self.PEER_ALIVE_REQ_PKT   = (PEER_ALIVE_REQ + self._local_id + self.TS_FLAGS)
            self.PEER_ALIVE_REPLY_PKT = (PEER_ALIVE_REPLY + self._local_id + self.TS_FLAGS)
            logger.info('(%s) IPSC Instance Created', self._network)
        else:
            # If we didn't get called correctly, log it!
            #
            logger.error('(%s) IPSC Instance Could Not be Created... Exiting', self._network)
            sys.exit()


    # This is called by REACTOR when it starts, We use it to set up the timed
    # loop for each instance of the IPSC engine
    #       
    def startProtocol(self):
        # Timed loops for:
        #   IPSC connection establishment and maintenance
        #   Reporting/Housekeeping
        #
        self._maintenance = task.LoopingCall(self.maintenance_loop)
        self._maintenance_loop = self._maintenance.start(self._local['ALIVE_TIMER'])
        #
        self._reporting = task.LoopingCall(self.reporting_loop)
        self._reporting_loop = self._reporting.start(10)

    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************

    def call_ctl_1(self, _network, _data):
        print('({}) Call Control Type 1 Packet Received' .format(_network))
    
    def call_ctl_2(self, _network, _data):
        print('({}) Call Control Type 2 Packet Received' .format(_network))
    
    def call_ctl_3(self, _network, _data):
        print('({}) Call Control Type 3 Packet Received' .format(_network))
    
    def xcmp_xnl(self, _network, _data):
        #print('({}) XCMP/XNL Packet Received' .format(_network))
        pass
        
    def group_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
        _peerid     = get_info(int_id(_peerid), peer_ids)
        _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
        print('({}) Group Voice Packet Received From: {}, IPSC Peer {}, Destination {}' .format(_network, _src_sub, _peerid, _dst_sub))
    
    def private_voice(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        _dst_sub    = get_info(int_id(_dst_sub), subscriber_ids)
        _peerid     = get_info(int_id(_peerid), peer_ids)
        _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
        print('({}) Private Voice Packet Received From: {}, IPSC Peer {}, Destination {}' .format(_network, _src_sub, _peerid, _dst_sub))
    
    def group_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        _dst_sub    = get_info(int_id(_dst_sub), talkgroup_ids)
        _peerid     = get_info(int_id(_peerid), peer_ids)
        _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
        print('({}) Group Data Packet Received From: {}, IPSC Peer {}, Destination {}' .format(_network, _src_sub, _peerid, _dst_sub))
    
    def private_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        _dst_sub    = get_info(int_id(_dst_sub), subscriber_ids)
        _peerid     = get_info(int_id(_peerid), peer_ids)
        _src_sub    = get_info(int_id(_src_sub), subscriber_ids)
        print('({}) Private Data Packet Received From: {}, IPSC Peer {}, Destination {}' .format(_network, _src_sub, _peerid, _dst_sub))

    def unknown_message(self, _network, _packettype, _peerid, _data):
        _time = time.strftime('%m/%d/%y %H:%M:%S')
        _packettype = h(_packettype)
        _peerid = get_info(int_id(_peerid), peer_ids)
        print('{} ({}) Unknown message type encountered\n\tPacket Type: {}\n\tFrom: {}' .format(_time, _network, _packettype, _peerid))
        print('\t', h(_data))


    # Take a packet to be SENT, calcualte auth hash and return the whole thing
    #
    def hashed_packet(self, _key, _data):
        _hash = binascii.a2b_hex((hmac.new(_key,_data,hashlib.sha1)).hexdigest()[:20])
        return (_data + _hash)    
    
    # Remove the hash from a packet and return the payload
    #
    def strip_hash(self, _data):
        return _data[:-10]
    
    # Take a RECEIVED packet, calculate the auth hash and verify authenticity
    #
    def validate_auth(self, _key, _data):
        _payload = self.strip_hash(_data)
        _hash = _data[-10:]
        _chk_hash = binascii.a2b_hex((hmac.new(_key,_payload,hashlib.sha1)).hexdigest()[:20])   

        if _chk_hash == _hash:
            return True
        else:
            return False


#************************************************
#     TIMED LOOP - MY CONNECTION MAINTENANCE
#************************************************
    
    def reporting_loop(self):
        # Right now, without this, we really dont' know anything is happening.  
        #print_master(self._network)
        #print_peer_list(self._network)
        logger.debug('(%s) Periodic Connection Maintenance Loop Started', self._network)
        pass
    
    def maintenance_loop(self):
        
        # If the master isn't connected, we have to do that before we can do anything else!
        #
        if self._master_stat['CONNECTED'] == False:
            reg_packet = self.hashed_packet(self._local['AUTH_KEY'], self.MASTER_REG_REQ_PKT)
            self.transport.write(reg_packet, (self._master_sock))
        
        # Once the master is connected, we have to send keep-alives.. and make sure we get them back
        elif (self._master_stat['CONNECTED'] == True):
            # Send keep-alive to the master
            master_alive_packet = self.hashed_packet(self._local['AUTH_KEY'], self.MASTER_ALIVE_PKT)
            self.transport.write(master_alive_packet, (self._master_sock))
            
            # If we had a keep-alive outstanding by the time we send another, mark it missed.
            if (self._master_stat['KEEP_ALIVES_OUTSTANDING']) > 0:
                self._master_stat['KEEP_ALIVES_MISSED'] += 1
                logger.info('(%s) Master Keep-Alive Missed', self._network)
            
            # If we have missed too many keep-alives, de-regiseter the master and start over.
            if self._master_stat['KEEP_ALIVES_OUTSTANDING'] >= self._local['MAX_MISSED']:
                self._master_stat['CONNECTED'] = False
                logger.error('(%s) Maximum Master Keep-Alives Missed -- De-registering the Master', self._network)
            
            # Update our stats before we move on...
            self._master_stat['KEEP_ALIVES_SENT'] += 1
            self._master_stat['KEEP_ALIVES_OUTSTANDING'] += 1
            
        else:
            # This is bad. If we get this message, we need to reset the state and try again
            logger.error('->> (%s) Master in UNKOWN STATE:%s:%s', self._network, self._master_sock)
            self._master_stat['CONNECTED'] == False
        
        
        # If the master is connected and we don't have a peer-list yet....
        #
        if  ((self._master_stat['CONNECTED'] == True) and (self._master_stat['PEER_LIST'] == False)):
            # Ask the master for a peer-list
            peer_list_req_packet = self.hashed_packet(self._local['AUTH_KEY'], self.PEER_LIST_REQ_PKT)
            self.transport.write(peer_list_req_packet, (self._master_sock))
            logger.info('(%s), No Peer List - Requesting One From the Master', self._network)


        # If we do have a peer-list, we need to register with the peers and send keep-alives...
        #
        if (self._master_stat['PEER_LIST'] == True):
            # Iterate the list of peers... so we do this for each one.
            for peer_id in self._peers.keys():
                peer = self._peers[peer_id]

                # We will show up in the peer list, but shouldn't try to talk to ourselves.
                if peer_id == self._local_id:
                    continue

                # If we haven't registered to a peer, send a registration
                if peer['STATUS']['CONNECTED'] == False:
                    peer_reg_packet = self.hashed_packet(self._local['AUTH_KEY'], self.PEER_REG_REQ_PKT)
                    self.transport.write(peer_reg_packet, (peer['IP'], peer['PORT']))
                    logger.info('(%s) Registering with Peer %s', self._network, int_id(peer_id))

                # If we have registered with the peer, then send a keep-alive
                elif peer['STATUS']['CONNECTED'] == True:
                    peer_alive_req_packet = self.hashed_packet(self._local['AUTH_KEY'], self.PEER_ALIVE_REQ_PKT)
                    self.transport.write(peer_alive_req_packet, (peer['IP'], peer['PORT']))

                    # If we have a keep-alive outstanding by the time we send another, mark it missed.
                    if peer['STATUS']['KEEP_ALIVES_OUTSTANDING'] > 0:
                        peer['STATUS']['KEEP_ALIVES_MISSED'] += 1
                        logger.info('(%s) Peer Keep-Alive Missed for %s', self._network, int_id(peer_id))

                    # If we have missed too many keep-alives, de-register the peer and start over.
                    if peer['STATUS']['KEEP_ALIVES_OUTSTANDING'] >= self._local['MAX_MISSED']:
                        peer['STATUS']['CONNECTED'] = False
                        del peer                        # Becuase once it's out of the dictionary, you can't use it for anything else.
                        logger.warning('(%s) Maximum Peer Keep-Alives Missed -- De-registering the Peer: %s', self._network, int_id(peer_id))
                    
                    # Update our stats before moving on...
                    peer['STATUS']['KEEP_ALIVES_SENT'] += 1
                    peer['STATUS']['KEEP_ALIVES_OUTSTANDING'] += 1
    
    
    # For public display of information, etc. - anything not part of internal logging/diagnostics
    #
    def _notify_event(self, network, event, info):
        """
            Used internally whenever an event happens that may be useful to notify the outside world about.
            Arguments:
                network: string, network name to look up in config
                event:   string, basic description
                info:    dict, in the interest of accomplishing as much as possible without code changes.
                         The dict will typically contain a peer_id so the origin of the event is known.
        """
        pass
    
    
#************************************************
#     RECEIVED DATAGRAM - ACT IMMEDIATELY!!!
#************************************************

    # Actions for recieved packets by type: For every packet recieved, there are some things that we need to do:
    #   Decode some of the info
    #   Check for auth and authenticate the packet
    #   Strip the hash from the end... we don't need it anymore
    #
    # Once they're done, we move on to the proccessing or callbacks for each packet type.
    #
    def datagramReceived(self, data, (host, port)):
        _packettype = data[0:1]
        _peerid     = data[1:5]
        
        # Authenticate the packet
        if self.validate_auth(self._local['AUTH_KEY'], data) == False:
            logger.warning('(%s) AuthError: IPSC packet failed authentication. Type %s: Peer ID: %s', self._network, h(_packettype), int(h(_peerid), 16))
            return
            
        # Strip the hash, we won't need it anymore
        data = self.strip_hash(data)

        # Packets types that must be originated from a peer (including master peer)
        if (_packettype in ANY_PEER_REQUIRED):
            if not(valid_master(self._network, _peerid) == False or valid_peer(self._peers.keys(), _peerid) == False):
                logger.warning('(%s) PeerError: Peer not in peer-list: %s', self._network, int(h(_peerid), 16))
                return
                
            # User, as in "subscriber" generated packets - a.k.a someone trasmitted
            if (_packettype in USER_PACKETS):
                # Extract commonly used items from the packet header
                _src_sub    = data[6:9]
                _dst_sub    = data[9:12]
                _call       = int_id(data[17:18])
                _ts         = bool(_call & TS_CALL_MSK)
                _end        = bool(_call & END_MSK)

                # User Voice and Data Call Types:
                if (_packettype == GROUP_VOICE):
                    self._notify_event(self._network, 'group_voice', {'peer_id': int(h(_peerid), 16)})
                    self.group_voice(self._network, _src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
            
                elif (_packettype == PVT_VOICE):
                    self._notify_event(self._network, 'private_voice', {'peer_id': int(h(_peerid), 16)})
                    self.private_voice(self._network, _src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
                    
                elif (_packettype == GROUP_DATA):
                    self._notify_event(self._network, 'group_data', {'peer_id': int(h(_peerid), 16)})
                    self.group_data(self._network, _src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
                    
                elif (_packettype == PVT_DATA):
                    self._notify_event(self._network, 'private_voice', {'peer_id': int(h(_peerid), 16)})
                    self.private_data(self._network, _src_sub, _dst_sub, _ts, _end, _peerid, data)
                    return
                return
                
            # Other peer-required types that we don't do much or anything with yet   
            elif (_packettype == XCMP_XNL):
                self.xcmp_xnl(self._network, data)
                return
            
            elif (_packettype == CALL_CTL_1):
                self.call_ctl_1(self._network, data)
                return
                
            elif (_packettype == CALL_CTL_2):
                self.call_ctl_2(self._network, data)
                return
                
            elif (_packettype == CALL_CTL_3):
                self.call_ctl_3(self._network, data)
                return
                
            # Connection maintenance packets that fall into this category
            elif (_packettype == DE_REG_REQ):
                de_register_peer(self._network, _peerid)
                logger.warning('(%s) Peer De-Registration Request From:%s:%s', self._network, host, port)
                return
            
            elif (_packettype == DE_REG_REPLY):
                logger.warning('(%s) Peer De-Registration Reply From:%s:%s', self._network, host, port)
                return
                
            elif (_packettype == RPT_WAKE_UP):
                logger.debug('(%s) Repeater Wake-Up Packet From:%s:%s', self._network, host, port)
                return
            return


        # Packets types that must be originated from a peer
        if (_packettype in PEER_REQUIRED):
            if valid_peer(self._peers.keys(), _peerid) == False:
                logger.warning('(%s) PeerError: Peer %s not in peer-list: %s', self._network, int(h(_peerid), 16), self._peers.keys())
                return
            
            # Packets we send...
            if (_packettype == PEER_ALIVE_REQ):
                # Generate a hashed paket from our template and send it.
                peer_alive_reply_packet = self.hashed_packet(self._local['AUTH_KEY'], self.PEER_ALIVE_REPLY_PKT)
                self.transport.write(peer_alive_reply_packet, (host, port))
                return
                                
            elif (_packettype == PEER_REG_REQ):
                peer_reg_reply_packet = self.hashed_packet(self._local['AUTH_KEY'], self.PEER_REG_REPLY_PKT)
                self.transport.write(peer_reg_reply_packet, (host, port))
                return
                
            # Packets we receive...
            elif (_packettype == PEER_ALIVE_REPLY):
                if _peerid in self._peers.keys():
                    self._peers[_peerid]['STATUS']['KEEP_ALIVES_OUTSTANDING'] = 0
                return                

            elif (_packettype == PEER_REG_REPLY):
                if _peerid in self._peers.keys():
                    self._peers[_peerid]['STATUS']['CONNECTED'] = True
                return
            return
        
        
        # Packets types that must be originated from a Master
        # Packets we receive...
        if (_packettype in MASTER_REQUIRED):
            if valid_master(self._network, _peerid) == False:
                logger.warning('(%s) MasterError: %s is not the master peer', self._network, int(h(_peerid), 16))
                return
                
            if (_packettype == MASTER_ALIVE_REPLY):
                # This action is so simple, it doesn't require a callback function, master is responding, we're good.
                self._master_stat['KEEP_ALIVES_OUTSTANDING'] = 0
                return
            
            elif (_packettype == PEER_LIST_REPLY):
                NETWORK[self._network]['MASTER']['STATUS']['PEER_LIST'] = True
                if len(data) > 18:
                    process_peer_list(data, self._network)
                return
            return
            
        
        # When we hear from the maseter, record it's ID, flag that we're connected, and reset the dead counter.
        elif (_packettype == MASTER_REG_REPLY):
            self._master['RADIO_ID'] = _peerid
            self._master_stat['CONNECTED'] = True
            self._master_stat['KEEP_ALIVES_OUTSTANDING'] = 0
            return
        
        # We know about these types, but absolutely don't take an action
        elif (_packettype == MASTER_REG_REQ):
            # We can't operate as a master as of now, so we should never receive one of these.
            logger.debug('(%s) Master Registration Packet Recieved - WE ARE NOT A MASTER!', self._network)
            return 
            
        # If there's a packet type we don't know aobut, it should be logged so we can figure it out and take an appropriate action!    
        else:
            self.unknown_message(self._network, _packettype, _peerid, data)
            return


#************************************************
#     Derived Class
#       used in the rare event of an
#       unauthenticated IPSC network.
#************************************************

class UnauthIPSC(IPSC):
    
    # There isn't a hash to build, so just return the data
    #
    def hashed_packet(self, _key, _data):
        return _data
    
    # Remove the hash from a packet and return the payload... except don't
    #
    def strip_hash(_self, _data):
        return _data
    
    # Everything is validated, so just return True
    #
    def validate_auth(self, _key, _data):
        return True
    

#************************************************
#      MAIN PROGRAM LOOP STARTS HERE
#************************************************

if __name__ == '__main__':
    logger.info('DMRlink \'dmrlink.py\' (c) 2013 N0MJS & the K0USY Group - SYSTEM STARTING...')
    networks = {}
    for ipsc_network in NETWORK:
        if (NETWORK[ipsc_network]['LOCAL']['ENABLED']):
            if NETWORK[ipsc_network]['LOCAL']['AUTH_ENABLED'] == True:
                networks[ipsc_network] = IPSC(ipsc_network)
            else:
                networks[ipsc_network] = UnauthIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network])
    reactor.run()
