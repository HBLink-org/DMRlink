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
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as ahex
from time import time
from importlib import import_module

import sys

from dmr_utils.utils import hex_str_3, hex_str_4, int_id

from dmrlink import IPSC, mk_ipsc_systems, systems, reportFactory, REPORT_OPCODES, build_aliases, config_reports
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


# Import Bridging rules
# Note: A stanza *must* exist for any IPSC configured in the main
# configuration file and listed as "active". It can be empty, 
# but it has to exist.
#
def build_rules(_bridge_rules):
    try:
        rule_file = import_module(_bridge_rules)
        logger.info('Bridge rules file found and rules imported')
    except ImportError:
        sys.exit('Bridging rules file not found or invalid')

    # Convert integer GROUP ID numbers from the config into hex strings
    # we need to send in the actual data packets.
    #

    for _ipsc in rule_file.RULES:
        for _rule in rule_file.RULES[_ipsc]['GROUP_VOICE']:
            _rule['SRC_GROUP']  = hex_str_3(_rule['SRC_GROUP'])
            _rule['DST_GROUP']  = hex_str_3(_rule['DST_GROUP'])
            _rule['SRC_TS']     = _rule['SRC_TS']
            _rule['DST_TS']     = _rule['DST_TS']
            for i, e in enumerate(_rule['ON']):
                _rule['ON'][i]  = hex_str_3(_rule['ON'][i])
            for i, e in enumerate(_rule['OFF']):
                _rule['OFF'][i] = hex_str_3(_rule['OFF'][i])
            _rule['TIMEOUT']= _rule['TIMEOUT']*60
            _rule['TIMER']      = time() + _rule['TIMEOUT']
        if _ipsc not in CONFIG['SYSTEMS']:
            sys.exit('ERROR: Bridge rules found for an IPSC network not configured in main configuration')
    for _ipsc in CONFIG['SYSTEMS']:
        if _ipsc not in rule_file.RULES:
            sys.exit('ERROR: Bridge rules not found for all IPSC network configured')

    return rule_file.RULES

# Import List of Bridges
# This is how we identify known bridges. If one of these is present
# and it's mode byte is set to bridge, we don't
#
def build_bridges(_known_bridges):
    try:
        bridges_file = import_module(_known_bridges)
        logger.info('Known bridges file found and bridge ID list imported ')
        return bridges_file.BRIDGES
    except ImportError:
        logger.critical('\'known_bridges.py\' not found - backup bridge service will not be enabled')
        return []
    

# Import subscriber ACL
# ACL may be a single list of subscriber IDs
# Global action is to allow or deny them. Multiple lists with different actions and ranges
# are not yet implemented.
def build_acl(_sub_acl):
    try:
        logger.info('ACL file found, importing entries. This will take about 1.5 seconds per 1 million IDs')
        acl_file = import_module(_sub_acl)
        sections = acl_file.ACL.split(':')
        ACL_ACTION = sections[0]
        entries_str = sections[1]
        ACL = set()
        
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
    logger.debug('(ALL IPSC) Rule timer loop started')
    _now = time()
    for _network in RULES:
        for _rule in RULES[_network]['GROUP_VOICE']:
            if _rule['TO_TYPE'] == 'ON':
                if _rule['ACTIVE'] == True:
                    if _rule['TIMER'] < _now:
                        _rule['ACTIVE'] = False
                        logger.info('(%s) Rule timout DEACTIVATE: Rule name: %s, Target IPSC: %s, TS: %s, TGID: %s', _network, _rule['NAME'], _rule['DST_NET'], _rule['DST_TS'], int_id(_rule['DST_GROUP']))
                    else:
                        timeout_in = _rule['TIMER'] - _now
                        logger.info('(%s) Rule ACTIVE with ON timer running: Timeout eligible in: %ds, Rule name: %s, Target IPSC: %s, TS: %s, TGID: %s', _network, timeout_in, _rule['NAME'], _rule['DST_NET'], _rule['DST_TS'], int_id(_rule['DST_GROUP']))
            elif _rule['TO_TYPE'] == 'OFF':
                if _rule['ACTIVE'] == False:
                    if _rule['TIMER'] < _now:
                        _rule['ACTIVE'] = True
                        logger.info('(%s) Rule timout ACTIVATE: Rule name: %s, Target IPSC: %s, TS: %s, TGID: %s', _network, _rule['NAME'], _rule['DST_NET'], _rule['DST_TS'], int_id(_rule['DST_GROUP']))
                    else:
                        timeout_in = _rule['TIMER'] - _now
                        logger.info('(%s) Rule DEACTIVE with OFF timer running: Timeout eligible in: %ds, Rule name: %s, Target IPSC: %s, TS: %s, TGID: %s', _network, timeout_in, _rule['NAME'], _rule['DST_NET'], _rule['DST_TS'], int_id(_rule['DST_GROUP']))
            else:
                logger.debug('Rule timer loop made no rule changes')

    
class bridgeIPSC(IPSC):
    def __init__(self, _name, _config, _logger, report):
        IPSC.__init__(self, _name, _config, _logger, report)
        self.BRIDGES = BRIDGES
        if self.BRIDGES:
            self._logger.info('(%s) Initializing backup/polite bridging', self._system)
            self.BRIDGE = False
        else:
            self.BRIDGE = True
            self._logger.info('Initializing standard bridging')

        self.IPSC_STATUS = {
            1: {'RX_GROUP':'\x00', 'TX_GROUP':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'},
            2: {'RX_GROUP':'\x00', 'TX_GROUP':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'}
        }
        
        self.last_seq_id = '\x00'
        self.call_start = 0
        
    # Setup the backup/polite bridging maintenance loop (based on keep-alive timer)
    
    
    def startProtocol(self):
        IPSC.startProtocol(self)
        if self.BRIDGES:
            self._bridge_presence = task.LoopingCall(self.bridge_presence_loop)
            self._bridge_presence_loop = self._bridge_presence.start(self._local['ALIVE_TIMER'])

    # This is the backup/polite bridge maintenance loop
    def bridge_presence_loop(self):
        self._logger.debug('(%s) Bridge presence loop initiated', self._system)
        _temp_bridge = True
        for peer in self.BRIDGES:
            _peer = hex_str_4(peer)
        
            if _peer in self._peers.keys() and (self._peers[_peer]['MODE_DECODE']['TS_1'] or self._peers[_peer]['MODE_DECODE']['TS_2']):
                _temp_bridge = False
                self._logger.debug('(%s) Peer %s is an active bridge', self._system, int_id(_peer))
        
            if _peer == self._master['RADIO_ID'] \
                and self._master['STATUS']['CONNECTED'] \
                and (self._master['MODE_DECODE']['TS_1'] or self._master['MODE_DECODE']['TS_2']):
                _temp_bridge = False
                self._logger.debug('(%s) Master %s is an active bridge',self._system, int_id(_peer))
        
        if self.BRIDGE != _temp_bridge:
            self._logger.info('(%s) Changing bridge status to: %s', self._system, _temp_bridge )
        self.BRIDGE = _temp_bridge

    
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
        self._logger.debug('(%s) Group Voice Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_group))
        _burst_data_type = _data[30] # Determine the type of voice packet this is (see top of file for possible types)
        _seq_id = _data[5]
        
        now = time() # Mark packet arrival time -- we'll need this for call contention handling 
        
        for rule in RULES[self._system]['GROUP_VOICE']:
            _target = rule['DST_NET']               # Shorthand to reduce length and make it easier to read
            _status = systems[_target].IPSC_STATUS # Shorthand to reduce length and make it easier to read
            
            # This is the primary rule match to determine if the call will be routed.
            if (rule['SRC_GROUP'] == _dst_group and rule['SRC_TS'] == _ts and rule['ACTIVE'] == True) and (self.BRIDGE == True or systems[_target].BRIDGE == True):
                
                #
                # BEGIN CONTENTION HANDLING
                # 
                # If this is an inter-DMRlink trunk, this isn't necessary
                if RULES[self._system]['TRUNK'] == False: 
                    
                    # The rules for each of the 4 "ifs" below are listed here for readability. The Frame To Send is:
                    #   From a different group than last RX from this IPSC, but it has been less than Group Hangtime
                    #   From a different group than last TX to this IPSC, but it has been less than Group Hangtime
                    #   From the same group as the last RX from this IPSC, but from a different subscriber, and it has been less than TS Clear Time
                    #   From the same group as the last TX to this IPSC, but from a different subscriber, and it has been less than TS Clear Time
                    # The "continue" at the end of each means the next iteration of the for loop that tests for matching rules
                    #
                    if ((rule['DST_GROUP'] != _status[rule['DST_TS']]['RX_GROUP']) and ((now - _status[rule['DST_TS']]['RX_TIME']) < RULES[_target]['GROUP_HANGTIME'])):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            self._logger.info('(%s) Call not bridged to TGID%s, target active or in group hangtime: IPSC: %s, TS: %s, TGID: %s', self._system, int_id(rule['DST_GROUP']), _target, rule['DST_TS'], int_id(_status[rule['DST_TS']]['RX_GROUP']))
                        continue    
                    if ((rule['DST_GROUP'] != _status[rule['DST_TS']]['TX_GROUP']) and ((now - _status[rule['DST_TS']]['TX_TIME']) < RULES[_target]['GROUP_HANGTIME'])):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            self._logger.info('(%s) Call not bridged to TGID%s, target in group hangtime: IPSC: %s, TS: %s, TGID: %s', self._system, int_id(rule['DST_GROUP']), _target, rule['DST_TS'], int_id(_status[rule['DST_TS']]['TX_GROUP']))
                        continue
                    if (rule['DST_GROUP'] == _status[rule['DST_TS']]['RX_GROUP']) and ((now - _status[rule['DST_TS']]['RX_TIME']) < TS_CLEAR_TIME):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            self._logger.info('(%s) Call not bridged to TGID%s, matching call already active on target: IPSC: %s, TS: %s, TGID: %s', self._system, int_id(rule['DST_GROUP']), _target, rule['DST_TS'], int_id(_status[rule['DST_TS']]['RX_GROUP']))
                        continue
                    if (rule['DST_GROUP'] == _status[rule['DST_TS']]['TX_GROUP']) and (_src_sub != _status[rule['DST_TS']]['TX_SRC_SUB']) and ((now - _status[rule['DST_TS']]['TX_TIME']) < TS_CLEAR_TIME):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            self._logger.info('(%s) Call not bridged for subscriber %s, call bridge in progress on target: IPSC: %s, TS: %s, TGID: %s SUB: %s', self._system, int_id(_src_sub), _target, rule['DST_TS'], int_id(_status[rule['DST_TS']]['TX_GROUP']), int_id(_status[rule['DST_TS']]['TX_SRC_SUB']))
                        continue
                #
                # END CONTENTION HANDLING
                #
                
                #
                # BEGIN FRAME FORWARDING
                #     
                # Make a copy of the payload       
                _tmp_data = _data
                
                # Re-Write the IPSC SRC to match the target network's ID
                _tmp_data = _tmp_data.replace(_peerid, self._CONFIG['SYSTEMS'][_target]['LOCAL']['RADIO_ID'])
                
                # Re-Write the destination Group ID
                _tmp_data = _tmp_data.replace(_dst_group, rule['DST_GROUP'])
            
                # Re-Write IPSC timeslot value
                _call_info = int_id(_data[17:18])
                if rule['DST_TS'] == 1:
                    _call_info &= ~(1 << 5)
                elif rule['DST_TS'] == 2:
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
                    if rule['DST_TS'] == 1:
                        _burst_data_type = BURST_DATA_TYPE['SLOT1_VOICE']
                    elif rule['DST_TS'] == 1:
                        _burst_data_type = BURST_DATA_TYPE['SLOT2_VOICE']
                    _tmp_data = _tmp_data[:30] + _burst_data_type + _tmp_data[31:]

                # Send the packet to all peers in the target IPSC
                systems[_target].send_to_ipsc(_tmp_data)
                #
                # END FRAME FORWARDING
                #
                
                
                # Set values for the contention handler to test next time there is a frame to forward
                _status[_ts]['TX_GROUP'] = rule['DST_GROUP']
                _status[_ts]['TX_TIME'] = now
                _status[_ts]['TX_SRC_SUB'] = _src_sub
                

        # Mark the group and time that a packet was recieved for the contention handler to use later
        self.IPSC_STATUS[_ts]['RX_GROUP'] = _dst_group
        self.IPSC_STATUS[_ts]['RX_TIME']  = now
        
        
        #
        # BEGIN IN-BAND SIGNALING BASED ON TGID & VOICE TERMINATOR FRAME
        #
        # Activate/Deactivate rules based on group voice activity -- PTT or UA for you c-Bridge dorks.
        # This will ONLY work for symmetrical rules!!!
        
        # Action happens on key up
        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
            if self.last_seq_id != _seq_id:
                self.last_seq_id = _seq_id
                self.call_start = time()
                self._logger.info('(%s) GROUP VOICE START: CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group))
        
        # Action happens on un-key
        if _burst_data_type == BURST_DATA_TYPE['VOICE_TERM']:
            if self.last_seq_id == _seq_id:
                self.call_duration = time() - self.call_start
                self._logger.info('(%s) GROUP VOICE END:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s Duration: %.2fs', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group), self.call_duration)
            else:
                self._logger.warning('(%s) GROUP VOICE END WITHOUT MATCHING START:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group),)
            
            # Iterate the rules dictionary
            for rule in RULES[self._system]['GROUP_VOICE']:
                _target = rule['DST_NET']
                
                # TGID matches a rule source, reset its timer
                if _ts == rule['SRC_TS'] and _dst_group == rule['SRC_GROUP'] and ((rule['TO_TYPE'] == 'ON' and (rule['ACTIVE'] == True)) or (rule['TO_TYPE'] == 'OFF' and rule['ACTIVE'] == False)):
                    rule['TIMER'] = now + rule['TIMEOUT']
                    self._logger.info('(%s) Source group transmission match for rule \"%s\". Reset timeout to %s', self._system, rule['NAME'], rule['TIMER'])
                    
                    # Scan for reciprocal rules and reset their timers as well.
                    for target_rule in RULES[_target]['GROUP_VOICE']:
                        if target_rule['NAME'] == rule['NAME']:
                            target_rule['TIMER'] = now + target_rule['TIMEOUT']
                            self._logger.info('(%s) Reciprocal group transmission match for rule \"%s\" on IPSC \"%s\". Reset timeout to %s', self._system, target_rule['NAME'], _target, rule['TIMER'])
                
                # TGID matches an ACTIVATION trigger
                if _dst_group in rule['ON']:
                    # Set the matching rule as ACTIVE
                    rule['ACTIVE'] = True
                    rule['TIMER'] = now + rule['TIMEOUT']
                    self._logger.info('(%s) Primary Bridge Rule \"%s\" changed to state: %s', self._system, rule['NAME'], rule['ACTIVE'])
                    
                    # Set reciprocal rules for other IPSCs as ACTIVE
                    for target_rule in RULES[_target]['GROUP_VOICE']:
                        if target_rule['NAME'] == rule['NAME']:
                            target_rule['ACTIVE'] = True
                            target_rule['TIMER'] = now + target_rule['TIMEOUT']
                            self._logger.info('(%s) Reciprocal Bridge Rule \"%s\" in IPSC \"%s\" changed to state: %s', self._system, target_rule['NAME'], _target, rule['ACTIVE'])
                            
                # TGID matches an DE-ACTIVATION trigger
                if _dst_group in rule['OFF']:
                    # Set the matching rule as ACTIVE
                    rule['ACTIVE'] = False
                    self._logger.info('(%s) Bridge Rule \"%s\" changed to state: %s', self._system, rule['NAME'], rule['ACTIVE'])
                    
                    # Set reciprocal rules for other IPSCs as ACTIVE
                    _target = rule['DST_NET']
                    for target_rule in RULES[_target]['GROUP_VOICE']:
                        if target_rule['NAME'] == rule['NAME']:
                            target_rule['ACTIVE'] = False
                            self._logger.info('(%s) Reciprocal Bridge Rule \"%s\" in IPSC \"%s\" changed to state: %s', self._system, target_rule['NAME'], _target, rule['ACTIVE'])
        #                    
        # END IN-BAND SIGNALLING
        #


    def group_data(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        self._logger.debug('(%s) Group Data Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))
        
        for target in RULES[self._system]['GROUP_DATA']:
            
            if self.BRIDGE == True or systems[target].BRIDGE == True:
                _tmp_data = _data
                # Re-Write the IPSC SRC to match the target network's ID
                _tmp_data = _tmp_data.replace(_peerid, self._CONFIG[target]['LOCAL']['RADIO_ID'])

                # Send the packet to all peers in the target IPSC
                systems[target].send_to_ipsc(_tmp_data)

    def private_data(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        self._logger.debug('(%s) Private Data Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))
        
        for target in RULES[self._system]['PRIVATE_DATA']:
                   
            if self.BRIDGE == True or systems[target].BRIDGE == True:
                _tmp_data = _data
                # Re-Write the IPSC SRC to match the target network's ID
                _tmp_data = _tmp_data.replace(_peerid, self._CONFIG[target]['LOCAL']['RADIO_ID'])

                # Send the packet to all peers in the target IPSC
                systems[target].send_to_ipsc(_tmp_data)

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
    
    
    
    # BRIDGE.PY SPECIFIC ITEMS GO HERE:
    
    # Build the routing rules file
    RULES = build_rules('bridge_rules')
    
    # Build list of known bridge IDs
    BRIDGES = build_bridges('known_bridges')

    # Build the Access Control List
    ACL = build_acl('sub_acl')
        
    # INITIALIZE THE REPORTING LOOP IF CONFIGURED
    rule_timer = task.LoopingCall(rule_timer_loop)
    rule_timer.start(60)
    
    
    
    # MAIN INITIALIZATION ITEMS HERE
    
    # INITIALIZE THE REPORTING LOOP
    report_server = config_reports(CONFIG, logger, reportFactory)
    
    # Build ID Aliases
    peer_ids, subscriber_ids, talkgroup_ids, local_ids = build_aliases(CONFIG, logger)
        
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGURED IPSC
    systems = mk_ipsc_systems(CONFIG, logger, systems, bridgeIPSC, report_server)

  
  
    # INITIALIZATION COMPLETE -- START THE REACTOR
    reactor.run()
