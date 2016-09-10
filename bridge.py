#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# This is a sample application to bridge traffic between IPSC networks. it uses
# one required (bridge_rules.py) and one optional (known_bridges.py) additional
# configuration files. Both files have their own documentation for use.
#
# "bridge_rules" contains the IPSC network, Timeslot and TGID matching rules to
# determine which voice calls are bridged between IPSC networks and which are
# not.
#
# "known_bridges" contains DMR radio ID numbers of known bridges. This file is
# used when you want bridge.py to be "polite" or serve as a backup bridge. If
# a known bridge exists in either a source OR target IPSC network, then no
# bridging between those IPSC networks will take place. This behavior is
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

from __future__ import print_function
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h
from time import time

# For debugging
from pprint import pprint

import sys
from dmrlink import IPSC, NETWORK, networks, REPORTS, reporting_loop, dmr_nat, logger, hex_str_3, hex_str_4, int_id

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2013 - 2016 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF; Steve Zingman, N4IRS; Mike Zingman, N4IRR'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'beta'


# Constants for this application
#
BURST_DATA_TYPE = {
    'VOICE_HEAD':  '\x01',
    'VOICE_TERM':  '\x02',
    'SLOT1_VOICE': '\x0A',
    'SLOT2_VOICE': '\x8A'   
}

# Minimum time between different subscribers transmitting on the same TGID
#
TS_CLEAR_TIME = .2

# Import Bridging rules
# Note: A stanza *must* exist for any IPSC configured in the main
# configuration file and listed as "active". It can be empty, 
# but it has to exist.
#
try:
    from bridge_rules import RULES as RULES_FILE
    logger.info('Bridge rules file found and rules imported')
except ImportError:
    sys.exit('Bridging rules file not found or invalid')

# Convert integer GROUP ID numbers from the config into hex strings
# we need to send in the actual data packets.
#

for _ipsc in RULES_FILE:
    for _rule in RULES_FILE[_ipsc]['GROUP_VOICE']:
        _rule['SRC_GROUP']  = hex_str_3(_rule['SRC_GROUP'])
        _rule['DST_GROUP']  = hex_str_3(_rule['DST_GROUP'])
        _rule['SRC_TS']     = _rule['SRC_TS'] - 1
        _rule['DST_TS']     = _rule['DST_TS'] - 1
        for i, e in enumerate(_rule['ON']):
            _rule['ON'][i]  = hex_str_3(_rule['ON'][i])
        for i, e in enumerate(_rule['OFF']):
            _rule['OFF'][i] = hex_str_3(_rule['OFF'][i])
        _rule['TIMEOUT']= _rule['TIMEOUT']*60
        _rule['TIMER']      = time() + _rule['TIMEOUT']
    if _ipsc not in NETWORK:
        sys.exit('ERROR: Bridge rules found for an IPSC network not configured in main configuration')
for _ipsc in NETWORK:
    if _ipsc not in RULES_FILE:
        sys.exit('ERROR: Bridge rules not found for all IPSC network configured')

RULES = RULES_FILE

# Import List of Bridges
# This is how we identify known bridges. If one of these is present
# and it's mode byte is set to bridge, we don't
#
try:
    from known_bridges import BRIDGES
    logger.info('Known bridges file found and bridge ID list imported ')
except ImportError:
    logger.critical('\'known_bridges.py\' not found - backup bridge service will not be enabled')
    BRIDGES = []

# Import subscriber ACL
# ACL may be a single list of subscriber IDs
# Global action is to allow or deny them. Multiple lists with different actions and ranges
# are not yet implemented.
try:
    from sub_acl import ACL_ACTION, ACL
    # uses more memory to build hex strings, but processes MUCH faster when checking for matches
    for i, e in enumerate(ACL):
        ACL[i] = hex_str_3(ACL[i])
    logger.info('Subscriber access control file found, subscriber ACL imported')
except ImportError:
    logger.critical('\'sub_acl.py\' not found - all subscriber IDs are valid')
    ACL_ACTION = 'NONE'

# Depending on which type of ACL is used (PERMIT, DENY... or there isn't one)
# define a differnet function to be used to check the ACL
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

# Run this every minute for rule timer updates
def rule_timer_loop():
    logger.debug('Rule timer loop started')
    _now = time()
    for _network in RULES:
        for _rule in RULES[_network]['GROUP_VOICE']:
            if _rule['TO_TYPE'] == 'ON':
                if _rule['ACTIVE'] == True:
                    if _rule['TIMER'] < _now:
                        _rule['ACTIVE'] = False
                        logger.info('(%s) Rule timout DEACTIVATE: Rule name: %s, Target IPSC: %s, TS: %s, TGID: %s', _network, _rule['NAME'], _rule['DST_NET'], _rule['DST_TS']+1, int_id(_rule['DST_GROUP']))
            elif _rule['TO_TYPE'] == 'OFF':
                if _rule['ACTIVE'] == False:
                    if _rule['TIMER'] < _now:
                        _rule['ACTIVE'] = True
                        logger.info('(%s) Rule timout ACTIVATE: Rule name: %s, Target IPSC: %s, TS: %s, TGID: %s', _network, _rule['NAME'], _rule['DST_NET'], _rule['DST_TS']+1, int_id(_rule['DST_GROUP']))
            else:
                logger.debug('Rule timer loop made no rule changes')

class bridgeIPSC(IPSC):
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        if BRIDGES:
            logger.info('Initializing backup/polite bridging')
            self.BRIDGE = False
        else:
            self.BRIDGE = True
            logger.info('Initializing standard bridging')

        self.IPSC_STATUS = {
            'TS1': {'RX_GROUP':'\x00', 'TX_GROUP':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'},
            'TS2': {'RX_GROUP':'\x00', 'TX_GROUP':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'}
        }
        
        self.last_seq_id = '\x00'
        self.call_start = 0
        
    # Setup the backup/polite bridging maintenance loop (based on keep-alive timer)
    
    if BRIDGES:
        def startProtocol(self):
            IPSC.startProtocol(self)

            self._bridge_presence = task.LoopingCall(self.bridge_presence_loop)
            self._bridge_presence_loop = self._bridge_presence.start(self._local['ALIVE_TIMER'])

    # This is the backup/polite bridge maintenance loop
    def bridge_presence_loop(self):
        _temp_bridge = True
        for peer in BRIDGES:
            _peer = hex_str_4(peer)
        
            if _peer in self._peers.keys() and (self._peers[_peer]['MODE_DECODE']['TS_1'] or self._peers[_peer]['MODE_DECODE']['TS_2']):
                _temp_bridge = False
                logger.debug('(%s) Peer %s is an active bridge', self._network, int_id(_peer))
        
            if _peer == self._master['RADIO_ID'] \
                and self._master['STATUS']['CONNECTED'] \
                and (self._master['MODE_DECODE']['TS_1'] or self._master['MODE_DECODE']['TS_2']):
                _temp_bridge = False
                logger.debug('(%s) Master %s is an active bridge',self._network, int_id(_peer))
        
        if self.BRIDGE != _temp_bridge:
            logger.info('(%s) Changing bridge status to: %s', self._network, _temp_bridge )
        self.BRIDGE = _temp_bridge

    
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def group_voice(self, _network, _src_sub, _dst_group, _ts, _end, _peerid, _data):
        
        # Check for ACL match, and return if the subscriber is not allowed
        if allow_sub(_src_sub) == False:
            logger.warning('(%s) Group Voice Packet ***REJECTED BY ACL*** From: %s, IPSC Peer %s, Destination %s', _network, int_id(_src_sub), int_id(_peerid), int_id(_dst_group))
            return
        
        # Process the packet
        logger.debug('(%s) Group Voice Packet Received From: %s, IPSC Peer %s, Destination %s', _network, int_id(_src_sub), int_id(_peerid), int_id(_dst_group))
        _burst_data_type = _data[30] # Determine the type of voice packet this is (see top of file for possible types)
        _seq_id = _data[5]
        if _ts == 0:
            _TS = 'TS1'
        elif _ts == 1:
            _TS = 'TS2'               
        
        now = time() # Mark packet arrival time -- we'll need this for call contention handling 
        
        for rule in RULES[_network]['GROUP_VOICE']:
            _target = rule['DST_NET']               # Shorthand to reduce length and make it easier to read
            _status = networks[_target].IPSC_STATUS # Shorthand to reduce length and make it easier to read

            # Matching for rules is against the Destination Group in the SOURCE packet (SRC_GROUP)
            # if rule['SRC_GROUP'] == _dst_group and rule['SRC_TS'] == _ts:
            # if BRIDGES:
            if (rule['SRC_GROUP'] == _dst_group and rule['SRC_TS'] == _ts and rule['ACTIVE'] == True) and (self.BRIDGE == True or networks[_target].BRIDGE == True):
                
                #
                # BEGIN CONTENTION HANDLING
                # 
                # If this is an inter-DMRlink trunk, this isn't necessary
                if RULES[_network]['TRUNK'] == False: 
                    
                    # The rules for each of the 4 "ifs" below are listed here for readability. The Frame To Send is:
                    #   From a different group than last RX from this IPSC, but it has been less than Group Hangtime
                    #   From a different group than last TX to this IPSC, but it has been less than Group Hangtime
                    #   From the same group as the last RX from this IPSC, but from a different subscriber, and it has been less than TS Clear Time
                    #   From the same group as the last TX to this IPSC, but from a different subscriber, and it has been less than TS Clear Time
                    # The "continue" at the end of each means the next iteration of the for loop that tests for matching rules
                    #
                    if ((rule['DST_GROUP'] != _status[_TS]['RX_GROUP']) and ((now - _status[_TS]['RX_TIME']) < RULES[_network]['GROUP_HANGTIME'])):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            logger.info('(%s) Call not bridged, target active or in group hangtime: IPSC %s, %s, TGID%s', _network, _target, _TS, int_id(rule['DST_GROUP']))
                        continue    
                    if ((rule['DST_GROUP'] != _status[_TS]['TX_GROUP']) and ((now - _status[_TS]['TX_TIME']) < RULES[_network]['GROUP_HANGTIME'])):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            logger.info('(%s) Call not bridged to destination on TGID %s, target in group hangtime: IPSC %s, %s, TGID%s', _network, int_id(_status[_TS]['TX_GROUP']), _target, _TS, int_id(rule['DST_GROUP']))
                        continue
                    if (rule['DST_GROUP'] == _status[_TS]['RX_GROUP']) and ((now - _status[_TS]['RX_TIME']) < TS_CLEAR_TIME):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            logger.info('(%s) Call not bridged, matching call already active on target: IPSC %s, %s, TGID%s', _network, _target, _TS, int_id(rule['DST_GROUP']))
                        continue
                    if (rule['DST_GROUP'] == _status[_TS]['TX_GROUP']) and (_src_sub != _status[_TS]['TX_SRC_SUB']) and ((now - _status[_TS]['TX_TIME']) < TS_CLEAR_TIME):
                        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
                            logger.info('(%s) Call not bridged, call bridge in progress from %s, target: IPSC %s, %s, TGID%s', _network, int_id(_src_sub), _target, _TS, int_id(rule['DST_GROUP']))
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
                _tmp_data = _tmp_data.replace(_peerid, NETWORK[_target]['LOCAL']['RADIO_ID'])
                
                # Re-Write the destination Group ID
                _tmp_data = _tmp_data.replace(_dst_group, rule['DST_GROUP'])
            
                # Re-Write IPSC timeslot value
                _call_info = int_id(_data[17:18])
                if rule['DST_TS'] == 0:
                    _call_info &= ~(1 << 5)
                elif rule['DST_TS'] == 1:
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
                    if rule['DST_TS'] == 0:
                        _burst_data_type = BURST_DATA_TYPE['SLOT1_VOICE']
                    elif rule['DST_TS'] == 1:
                        _burst_data_type = BURST_DATA_TYPE['SLOT2_VOICE']
                    _tmp_data = _tmp_data[:30] + _burst_data_type + _tmp_data[31:]

                # Send the packet to all peers in the target IPSC
                networks[_target].send_to_ipsc(_tmp_data)
                #
                # END FRAME FORWARDING
                #
                
                
                # Set values for the contention handler to test next time there is a frame to forward
                _status[_TS]['TX_GROUP'] = rule['DST_GROUP']
                _status[_TS]['TX_TIME'] = now
                _status[_TS]['TX_SRC_SUB'] = _src_sub
                

        # Mark the group and time that a packet was recieved for the contention handler to use later
        self.IPSC_STATUS[_TS]['RX_GROUP'] = _dst_group
        self.IPSC_STATUS[_TS]['RX_TIME']  = now
        
        
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
                logger.info('(%s) GROUP VOICE START: CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', _network, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts+1, int_id(_dst_group))
        
        # Action happens on un-key
        if _burst_data_type == BURST_DATA_TYPE['VOICE_TERM']:
            if self.last_seq_id == _seq_id:
                self.call_duration = time() - self.call_start
                logger.info('(%s) GROUP VOICE END:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s Duration: %.2fs', _network, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts+1, int_id(_dst_group), self.call_duration)
            else:
                logger.warning('(%s) GROUP VOICE END WITHOUT MATCHING START:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', _network, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts+1, int_id(_dst_group),)
            
            # Iterate the rules dictionary
            for rule in RULES[_network]['GROUP_VOICE']:
                _target = rule['DST_NET']
                
                # TGID matches a rule source, reset its timer
                if _ts == rule['SRC_TS'] and _dst_group == rule['SRC_GROUP'] and (rule['TO_TYPE'] == 'ON' or rule['TO_TYPE'] == 'OFF'):
                    rule['TIMER'] = now + rule['TIMEOUT']
                    logger.info('(%s) Source group transmission match for rule \"%s\". Reset timeout to %s', _network, rule['NAME'], rule['TIMER'])
                    
                    # Scan for reciprocal rules and reset their timers as well.
                    for target_rule in RULES[_target]['GROUP_VOICE']:
                        if target_rule['NAME'] == rule['NAME']:
                            target_rule['TIMER'] = now + target_rule['TIMEOUT']
                            logger.info('(%s) Reciprocal group transmission match for rule \"%s\" on IPSC \"%s\". Reset timeout to %s', _network, target_rule['NAME'], _target, rule['TIMER'])
                
                # TGID matches an ACTIVATION trigger
                if _dst_group in rule['ON']:
                    # Set the matching rule as ACTIVE
                    rule['ACTIVE'] = True
                    rule['TIMER'] = now + rule['TIMEOUT']
                    logger.info('(%s) Primary Bridge Rule \"%s\" changed to state: %s', _network, rule['NAME'], rule['ACTIVE'])
                    
                    # Set reciprocal rules for other IPSCs as ACTIVE
                    for target_rule in RULES[_target]['GROUP_VOICE']:
                        if target_rule['NAME'] == rule['NAME']:
                            target_rule['ACTIVE'] = True
                            target_rule['TIMER'] = now + target_rule['TIMEOUT']
                            logger.info('(%s) Reciprocal Bridge Rule \"%s\" in IPSC \"%s\" changed to state: %s', _network, target_rule['NAME'], _target, rule['ACTIVE'])
                            
                # TGID matches an DE-ACTIVATION trigger
                if _dst_group in rule['OFF']:
                    # Set the matching rule as ACTIVE
                    rule['ACTIVE'] = False
                    logger.info('(%s) Bridge Rule \"%s\" changed to state: %s', _network, rule['NAME'], rule['ACTIVE'])
                    
                    # Set reciprocal rules for other IPSCs as ACTIVE
                    _target = rule['DST_NET']
                    for target_rule in RULES[_target]['GROUP_VOICE']:
                        if target_rule['NAME'] == rule['NAME']:
                            target_rule['ACTIVE'] = False
                            logger.info('(%s) Reciprocal Bridge Rule \"%s\" in IPSC \"%s\" changed to state: %s', _network, target_rule['NAME'], _target, rule['ACTIVE'])
        #                    
        # END IN-BAND SIGNALLING
        #


    def group_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        logger.debug('(%s) Group Data Packet Received From: %s, IPSC Peer %s, Destination %s', _network, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))
        
        for target in RULES[_network]['GROUP_DATA']:
            
            if self.BRIDGE == True or networks[target].BRIDGE == True:
                _tmp_data = _data
                # Re-Write the IPSC SRC to match the target network's ID
                _tmp_data = _tmp_data.replace(_peerid, NETWORK[target]['LOCAL']['RADIO_ID'])

                # Send the packet to all peers in the target IPSC
                networks[target].send_to_ipsc(_tmp_data)

    def private_data(self, _network, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        logger.debug('(%s) Private Data Packet Received From: %s, IPSC Peer %s, Destination %s', _network, int_id(_src_sub), int_id(_peerid), int_id(_dst_sub))
        
        for target in RULES[_network]['PRIVATE_DATA']:
                   
            if self.BRIDGE == True or networks[target].BRIDGE == True:
                _tmp_data = _data
                # Re-Write the IPSC SRC to match the target network's ID
                _tmp_data = _tmp_data.replace(_peerid, NETWORK[target]['LOCAL']['RADIO_ID'])

                # Send the packet to all peers in the target IPSC
                networks[target].send_to_ipsc(_tmp_data)


if __name__ == '__main__':
    logger.info('DMRlink \'bridge.py\' (c) 2013-2015 N0MJS & the K0USY Group - SYSTEM STARTING...')
    
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGUED IPSC
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = bridgeIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    
    # INITIALIZE THE REPORTING LOOP IF CONFIGURED
    if REPORTS['REPORT_NETWORKS']:
        reporting = task.LoopingCall(reporting_loop)
        reporting.start(REPORTS['REPORT_INTERVAL'])
        
    # INITIALIZE THE REPORTING LOOP IF CONFIGURED
    rule_timer = task.LoopingCall(rule_timer_loop)
    rule_timer.start(60)
       
    reactor.run()