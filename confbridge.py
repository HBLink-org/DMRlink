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

# This is a sample application to bridge traffic between IPSC systems. it uses
# one required (bridge_rules.py) and one optional (known_bridges.py) additional
# configuration files. Both files have their own documentation for use.
#
# "bridge_rules" contains the IPSC network, Timeslot and TGID matching rules to
# determine which voice calls are bridged between IPSC systems and which are
# not.
#
# "known_bridges" contains DMR radio ID numbers of known bridges. This file is
# used when you want bridge.py to be "polite" or serve as a backup bridge. If
# a known bridge exists in either a source OR target IPSC network, then no
# bridging between those IPSC systems will take place. This behavior is
# dynamic and updates each keep-alive interval (main configuration file).
# For faster failover, configure a short keep-alive time and a low number of
# missed keep-alives before timout. I recommend 5 sec keep-alive and 3 missed.
# That gives a worst-case scenario of 15 seconds to fail over. Recovery will
# typically happen with a single "blip" in the transmission up to about 5
# seconds.
#
# While this file is listed as Beta status, K0USY Group depends on this code
# for the bridigng of it's many repeaters. We consider it reliable, but you
# get what you pay for... as usual, no guarantees.
#
# Use to make test strings: #print('PKT:', "\\x".join("{:02x}".format(ord(c)) for c in _data))

from __future__ import print_function

from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import NetstringReceiver
from twisted.internet import reactor
from twisted.internet import task

from binascii import b2a_hex as ahex
from time import time
from importlib import import_module

import cPickle as pickle

from dmr_utils.utils import hex_str_3, hex_str_4, int_id

from dmrlink import IPSC, mk_ipsc_systems, systems, reportFactory, REPORT_OPCODES, build_aliases
from ipsc.ipsc_const import BURST_DATA_TYPE


__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013 - 2016 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF; Steve Zingman, N4IRS; Mike Zingman, N4IRR'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


# Minimum time between different subscribers transmitting on the same TGID
#
TS_CLEAR_TIME = .2

# Declare this here so that we can define functions around it
#
BRIDGES = {}

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
            _server.send_bridge()
            
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

# Build the conference bridging structure from the bridge file.
#
def make_bridge_config(_confbridge_rules):
    try:
        bridge_file = import_module(_confbridge_rules)
        logger.info('Bridge configuration file found and imported')
    except ImportError:
        sys.exit('Bridge configuration file not found or invalid')

    # Convert integer GROUP ID numbers from the config into hex strings
    # we need to send in the actual data packets.
    #
    for _bridge in bridge_file.BRIDGES:
        for _system in bridge_file.BRIDGES[_bridge]:
            if _system['SYSTEM'] not in CONFIG['SYSTEMS']:
                sys.exit('ERROR: Conference bridges found for system not configured main configuration')
                
            _system['TGID']       = hex_str_3(_system['TGID'])
            for i, e in enumerate(_system['ON']):
                _system['ON'][i]  = hex_str_3(_system['ON'][i])
            for i, e in enumerate(_system['OFF']):
                _system['OFF'][i] = hex_str_3(_system['OFF'][i])
            for i, e in enumerate(_system['RESET']):
                _system['RESET'][i] = hex_str_3(_system['RESET'][i])
            _system['TIMEOUT']    = _system['TIMEOUT']*60
            _system['TIMER']      = time()

    return {'BRIDGE_CONF': bridge_file.BRIDGE_CONF, 'BRIDGES': bridge_file.BRIDGES, 'TRUNKS': bridge_file.TRUNKS}
    

# Import subscriber ACL
# ACL may be a single list of subscriber IDs
# Global action is to allow or deny them. Multiple lists with different actions and ranges
# are not yet implemented.
def build_acl(_sub_acl):
    ACL = set()
    try:
        logger.info('ACL file found, importing entries. This will take about 1.5 seconds per 1 million IDs')
        acl_file = import_module(_sub_acl)
        sections = acl_file.ACL.split(':')
        ACL_ACTION = sections[0]
        entries_str = sections[1]
        for entry in entries_str.split(','):
            if '-' in entry:
                start,end = entry.split('-')
                start,end = int(start), int(end)
                for id in range(start, end+1):
                    ACL.add(hex_str_3(id))
            else:
                id = int(entry)
                ACL.add(hex_str_3(id))
        
        logger.info('ACL loaded: action "{}" for {:,} radio IDs'.format(ACL_ACTION, len(ACL)))
    
    except ImportError:
        logger.info('ACL file not found or invalid - all subscriber IDs are valid')
        ACL_ACTION = 'NONE'

    # Depending on which type of ACL is used (PERMIT, DENY... or there isn't one)
    # define a differnet function to be used to check the ACL
    global allow_sub
    if ACL_ACTION == 'PERMIT':
        def allow_sub(_sub):
            if _sub in ACL:
                return True
            else:
                return False
    elif ACL_ACTION == 'DENY':
        def allow_sub(_sub):
            if _sub not in ACL:
                return True
            else:
                return False
    else:
        def allow_sub(_sub):
            return True
    
    return ACL


# Run this every minute for rule timer updates
def rule_timer_loop():
    logger.info('(ALL IPSC SYSTEMS) Rule timer loop started')
    _now = time()

    for _bridge in BRIDGES:
        for _system in BRIDGES[_bridge]:
            if _system['TO_TYPE'] == 'ON':
                if _system['ACTIVE'] == True:
                    if _system['TIMER'] < _now:
                        _system['ACTIVE'] = False
                        logger.info('Conference Bridge TIMEOUT: DEACTIVATE System: %s, Bridge: %s, TS: %s, TGID: %s', _system['SYSTEM'], _bridge, _system['TS'], int_id(_system['TGID']))
                    else:
                        timeout_in = _system['TIMER'] - _now
                        logger.info('Conference Bridge ACTIVE (ON timer running): System: %s Bridge: %s, TS: %s, TGID: %s, Timeout in: %ss,', _system['SYSTEM'], _bridge, _system['TS'], int_id(_system['TGID']),  timeout_in)
                elif _system['ACTIVE'] == False:
                    logger.debug('Conference Bridge INACTIVE (no change): System: %s Bridge: %s, TS: %s, TGID: %s', _system['SYSTEM'], _bridge, _system['TS'], int_id(_system['TGID']))
            elif _system['TO_TYPE'] == 'OFF':
                if _system['ACTIVE'] == False:
                    if _system['TIMER'] < _now:
                        _system['ACTIVE'] = True
                        logger.info('Conference Bridge TIMEOUT: ACTIVATE System: %s, Bridge: %s, TS: %s, TGID: %s', _system['SYSTEM'], _bridge, _system['TS'], int_id(_system['TGID']))
                    else:
                        timeout_in = _system['TIMER'] - _now
                        logger.info('Conference Bridge INACTIVE (OFF timer running): System: %s Bridge: %s, TS: %s, TGID: %s, Timeout in: %ss,', _system['SYSTEM'], _bridge, _system['TS'], int_id(_system['TGID']),  timeout_in)
                elif _system['ACTIVE'] == True:
                    logger.debug('Conference Bridge ACTIVE (no change): System: %s Bridge: %s, TS: %s, TGID: %s', _system['SYSTEM'], _bridge, _system['TS'], int_id(_system['TGID']))
            else:
                logger.debug('Conference Bridge NO ACTION: System: %s, Bridge: %s, TS: %s, TGID: %s', _system['SYSTEM'], _bridge, _system['TS'], int_id(_system['TGID']))

    if BRIDGE_CONF['REPORT'] == 'network':
        report_server.send_clients('bridge updated')

    
class confbridgeIPSC(IPSC):
    def __init__(self, _name, _config, _logger, _report):
        IPSC.__init__(self, _name, _config, _logger, _report)

        self.STATUS = {
            1: {'RX_TGID':'\x00', 'TX_TGID':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'},
            2: {'RX_TGID':'\x00', 'TX_TGID':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'}
        }
        
        self.last_seq_id = '\x00'
        self.call_start = 0

    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def group_voice(self, _src_sub, _dst_group, _ts, _end, _peerid, _data):

        # Check for ACL match, and return if the subscriber is not allowed
        if allow_sub(_src_sub) == False:
            self._logger.warning('(%s) Group Voice Packet ***REJECTED BY ACL*** From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_group))
            return
        
        # Process the packet
        #self._logger.debug('(%s) Group Voice Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_group))
        _burst_data_type = _data[30] # Determine the type of voice packet this is (see top of file for possible types)
        _seq_id = _data[5]
        
        now = time() # Mark packet arrival time -- we'll need this for call contention handling 
        
        for _bridge in BRIDGES:
            for _system in BRIDGES[_bridge]:

                if (_system['SYSTEM'] == self._system and _system['TGID'] == _dst_group and _system['TS'] == _ts and _system['ACTIVE'] == True):
                    
                    for _target in BRIDGES[_bridge]:
                        if _target['SYSTEM'] != self._system:
                            if _target['ACTIVE']:
                                _target_status = systems[_target['SYSTEM']].STATUS
                                _target_system = self._CONFIG['SYSTEMS'][_target['SYSTEM']]
                
                                # BEGIN CONTENTION HANDLING
                                #
                                # If the system is listed as a "TRUNK", there will be no contention handling. All traffic is forwarded to it
                                # 
                                # The rules for each of the 4 "ifs" below are listed here for readability. The Frame To Send is:
                                #   From a different group than last RX from this IPSC, but it has been less than Group Hangtime
                                #   From a different group than last TX to this IPSC, but it has been less than Group Hangtime
                                #   From the same group as the last RX from this IPSC, but from a different subscriber, and it has been less than TS Clear Time
                                #   From the same group as the last TX to this IPSC, but from a different subscriber, and it has been less than TS Clear Time
                                # The "continue" at the end of each means the next iteration of the for loop that tests for matching rules
                                #
                                if _target not in TRUNKS:                           
                                    if ((_target['TGID'] != _target_status[_target['TS']]['RX_TGID']) and ((now - _target_status[_target['TS']]['RX_TIME']) < _target_system['LOCAL']['GROUP_HANGTIME'])):
                                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                                            self._logger.info('(%s) Call not bridged to TGID%s, target active or in group hangtime: IPSC: %s, TS: %s, TGID: %s', self._system, int_id(_target['TGID']), _target['SYSTEM'], _target['TS'], int_id(_target_status[_target['TS']]['RX_TGID']))
                                        continue
                                    if ((_target['TGID'] != _target_status[_target['TS']]['TX_TGID']) and ((now - _target_status[_target['TS']]['TX_TIME']) < _target_system['LOCAL']['GROUP_HANGTIME'])):
                                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                                            self._logger.info('(%s) Call not bridged to TGID%s, target in group hangtime: IPSC: %s, TS: %s, TGID: %s', self._system, int_id(_target['TGID']), _target['SYSTEM'], _target['TS'], int_id(_target_status[_target['TS']]['TX_TGID']))
                                        continue
                                    if (_target['TGID'] == _target_status[_target['TS']]['RX_TGID']) and ((now - _target_status[_target['TS']]['RX_TIME']) < TS_CLEAR_TIME):
                                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                                            self._logger.info('(%s) Call not bridged to TGID%s, matching call already active on target: IPSC: %s, TS: %s, TGID: %s', self._system, int_id(_target['TGID']), _target['SYSTEM'], _target['TS'], int_id(_target_status[_target['TS']]['RX_TGID']))
                                        continue
                                    if (_target['TGID'] == _target_status[_target['TS']]['TX_TGID']) and (_src_sub != _target_status[_target['TS']]['TX_SRC_SUB']) and ((now - _target_status[_target['TS']]['TX_TIME']) < TS_CLEAR_TIME):
                                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                                            self._logger.info('(%s) Call not bridged for subscriber %s, call bridge in progress on target: IPSC: %s, TS: %s, TGID: %s SUB: %s', self._system, int_id(_src_sub), _target['SYSTEM'], _target['TGID'], int_id(_target_status[_target['TS']]['TX_TGID']), int_id(_target_status[_target['TS']]['TX_SRC_SUB']))
                                        continue
                                #
                                # END CONTENTION HANDLING
                                #

                                #
                                # BEGIN FRAME FORWARDING
                                #
                                # Make a copy of the payload
                                _tmp_data = _data
                                # Re-Write the PEER ID in the IPSC Header:
                                _tmp_data = _tmp_data.replace(_peerid,  _target_system['LOCAL']['RADIO_ID'], 1)

                                # Re-Write the IPSC SRC + DST GROUP in IPSC Headers:
                                _tmp_data = _tmp_data.replace(_src_sub + _dst_group, _src_sub + _target['TGID'], 1)

                                # Re-Write the DST GROUP + IPSC SRC in DMR LC (Header, Terminator and Voice Burst E):
                                _tmp_data = _tmp_data.replace(_dst_group + _src_sub, _target['TGID'] + _src_sub, 1)

                                # Re-Write IPSC timeslot value
                                _call_info = int_id(_data[17:18])
                                if _target['TS'] == 1:
                                    _call_info &= ~(1 << 5)
                                elif _target['TS'] == 2:
                                    _call_info |= 1 << 5
                                _call_info = chr(_call_info)
                                _tmp_data = _tmp_data[:17] + _call_info + _tmp_data[18:] 

                                # Re-Write DMR timeslot value
                                # Determine if the slot is present, so we can translate if need be
                                if _burst_data_type == BURST_DATA_TYPE['SLOT1_VOICE'] or _burst_data_type == BURST_DATA_TYPE['SLOT2_VOICE']:
                                    _slot_valid = True
                                else:
                                    _slot_valid = False
                                # Re-Write timeslot if necessary...
                                if _slot_valid:
                                    if _target['TS'] == 1:
                                        _burst_data_type = BURST_DATA_TYPE['SLOT1_VOICE']
                                    elif _target['TS'] == 1:
                                        _burst_data_type = BURST_DATA_TYPE['SLOT2_VOICE']
                                    _tmp_data = _tmp_data[:30] + _burst_data_type + _tmp_data[31:]

                                # Send the packet to all peers in the target IPSC
                                systems[_target['SYSTEM']].send_to_ipsc(_tmp_data)
                                #
                                # END FRAME FORWARDING
                                #

                                # Set values for the contention handler to test next time there is a frame to forward
                                _target_status[_target['TS']]['TX_TGID'] = _target['TGID']
                                _target_status[_target['TS']]['TX_TIME'] = now
                                _target_status[_target['TS']]['TX_SRC_SUB'] = _src_sub
                

        # Mark the group and time that a packet was recieved for the contention handler to use later
        self.STATUS[_ts]['RX_TGID'] = _dst_group
        self.STATUS[_ts]['RX_TIME']  = now
        
        
        #
        # BEGIN IN-BAND SIGNALING BASED ON TGID & VOICE TERMINATOR FRAME
        #
        # Activate/Deactivate rules based on group voice activity -- PTT or UA for you c-Bridge dorks.
        # This will ONLY work for symmetrical rules!!!
        
        # Action happens on key up
        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
            if self.last_seq_id != _seq_id or (self.call_start + TS_CLEAR_TIME) < now:
                self.last_seq_id = _seq_id
                self.call_start = now
                self._logger.info('(%s) GROUP VOICE START: CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group))
                if self._CONFIG['REPORTS']['REPORT_NETWORKS'] == 'NETWORK':
                    self._report.send_bridgeEvent('GROUP VOICE,START,{},{},{},{},{},{}'.format(self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group)))
                
        # Action happens on un-key
        if _burst_data_type == BURST_DATA_TYPE['VOICE_TERM']:
            if self.last_seq_id == _seq_id:
                self.call_duration = now - self.call_start
                self._logger.info('(%s) GROUP VOICE END:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s Duration: %.2fs', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group), self.call_duration)
                if self._CONFIG['REPORTS']['REPORT_NETWORKS'] == 'NETWORK':
                    self._report.send_bridgeEvent('GROUP VOICE,END,{},{},{},{},{},{},{:.2f}'.format(self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group), self.call_duration))
            else:
                self._logger.warning('(%s) GROUP VOICE END WITHOUT MATCHING START:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group))
                if self._CONFIG['REPORTS']['REPORT_NETWORKS'] == 'NETWORK':
                    self._report.send_bridgeEvent('GROUP VOICE,UNMATCHED END,{},{},{},{},{},{}'.format(self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group)))
                

            # Iterate the rules dictionary
            for _bridge in BRIDGES:
                for _system in BRIDGES[_bridge]:
                    if _system['SYSTEM'] == self._system:

                        # TGID matches an ACTIVATION trigger
                        if (_dst_group in _system['ON']  or _dst_group in _system['RESET']) and _ts == _system['TS']:
                            # Set the matching rule as ACTIVE
                            if _dst_group in _system['ON']:
                                if _system['ACTIVE'] == False:
                                    _system['ACTIVE'] = True
                                    self._logger.info('(%s) Bridge: %s, connection changed to state: %s', self._system, _bridge, _system['ACTIVE'])
                                    # Cancel the timer if we've enabled an "OFF" type timeout
                                    if _system['TO_TYPE'] == 'OFF':
                                        _system['TIMER'] = now
                                        self._logger.info('(%s) Bridge: %s set to "OFF" with an on timer rule: timeout timer cancelled', self._system, _bridge)
                            # Reset the timer for the rule
                            if _system['ACTIVE'] == True and _system['TO_TYPE'] == 'ON':
                                _system['TIMER'] = now + _system['TIMEOUT']
                                self._logger.info('(%s) Bridge: %s, timeout timer reset to: %s', self._system, _bridge, _system['TIMER'] - now)

                        # TGID matches an DE-ACTIVATION trigger
                        if (_dst_group in _system['OFF']  or _dst_group in _system['RESET']) and _ts == _system['TS']:
                            # Set the matching rule as ACTIVE
                            if _dst_group in _system['OFF']:
                                if _system['ACTIVE'] == True:
                                    _system['ACTIVE'] = False
                                    self._logger.info('(%s) Bridge: %s, connection changed to state: %s', self._system, _bridge, _system['ACTIVE'])
                                    # Cancel the timer if we've enabled an "ON" type timeout
                                    if _system['TO_TYPE'] == 'ON':
                                        _system['TIMER'] = now
                                        self._logger.info('(%s) Bridge: %s set to ON with and "OFF" timer rule: timeout timer cancelled', self._system, _bridge)
                            # Reset the timer for the rule
                            if _system['ACTIVE'] == False and _system['TO_TYPE'] == 'OFF':
                                _system['TIMER'] = now + _system['TIMEOUT']
                                self._logger.info('(%s) Bridge: %s, timeout timer reset to: %s', self._system, _bridge, _system['TIMER'] - now)
                            # Cancel the timer if we've enabled an "ON" type timeout
                            if _system['ACTIVE'] == True and _system['TO_TYPE'] == 'ON' and _dst_group in _system['OFF']:
                                _system['TIMER'] = now
                                self._logger.info('(%s) Bridge: %s set to ON with and "OFF" timer rule: timeout timer cancelled', self._system, _bridge)

        #
        # END IN-BAND SIGNALLING
        #

class confbridgeReportFactory(reportFactory):
        
    def send_bridge(self):
        serialized = pickle.dumps(BRIDGES, protocol=pickle.HIGHEST_PROTOCOL)
        self.send_clients(REPORT_OPCODES['BRIDGE_SND']+serialized)
        
    def send_bridgeEvent(self, _data):
        self.send_clients(REPORT_OPCODES['BRDG_EVENT']+_data)
        
    
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
    logger.info('DMRlink \'dmrlink.py\' (c) 2013 - 2015 N0MJS & the K0USY Group - SYSTEM STARTING...')
    
    # Set signal handers so that we can gracefully exit if need be
    def sig_handler(_signal, _frame):
        logger.info('*** DMRLINK IS TERMINATING WITH SIGNAL %s ***', str(_signal))
        for system in systems:
            systems[system].de_register_self()
        reactor.stop()
    
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
        signal.signal(sig, sig_handler)
    
    # INITIALIZE THE REPORTING LOOP
    report_server = config_reports(CONFIG, logger, confbridgeReportFactory)
    
    # Build ID Aliases
    peer_ids, subscriber_ids, talkgroup_ids, local_ids = build_aliases(CONFIG, logger)
        
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGURED IPSC
    systems = mk_ipsc_systems(CONFIG, logger, systems, confbridgeIPSC, report_server)



    # CONFBRIDGE.PY SPECIFIC ITEMS GO HERE:
    
    # Build the routing rules and other configuration
    CONFIG_DICT = make_bridge_config('confbridge_rules')
    BRIDGE_CONF = CONFIG_DICT['BRIDGE_CONF']
    TRUNKS      = CONFIG_DICT['TRUNKS']
    BRIDGES     = CONFIG_DICT['BRIDGES']

    # Build the Access Control List
    ACL = build_acl('sub_acl')
    
    # Initialize the rule timer loop
    rule_timer = task.LoopingCall(rule_timer_loop)
    rule_timer.start(60)
    
    # INITIALIZATION COMPLETE -- START THE REACTOR
    reactor.run()
