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
__copyright__   = 'Copyright (c) 2017 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF; Steve Zingman, N4IRS; Mike Zingman, N4IRR'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


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

    
class proxyIPSC(IPSC):
    def __init__(self, _name, _config, _logger, report):
        IPSC.__init__(self, _name, _config, _logger, report)
        
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
        self._logger.debug('(%s) Group Voice Packet Received From: %s, IPSC Peer %s, Destination %s', self._system, int_id(_src_sub), int_id(_peerid), int_id(_dst_group))
        _burst_data_type = _data[30] # Determine the type of voice packet this is (see top of file for possible types)
        _seq_id = _data[5]
        
        for system in systems:
            if system != self._system:
                #
                # BEGIN FRAME FORWARDING
                #     
                # Make a copy of the payload       
                _tmp_data = _data
            
                # Re-Write the IPSC SRC to match the target network's ID
                _tmp_data = _tmp_data.replace(_peerid, self._CONFIG['SYSTEMS'][system]['LOCAL']['RADIO_ID'])

                # Send the packet to all peers in the target IPSC
                systems[system].send_to_ipsc(_tmp_data)
                #
                # END FRAME FORWARDING
                #

        #
        # BEGIN IN-BAND SIGNALING BASED ON TGID & VOICE TERMINATOR FRAME
        #

        # Action happens on key up
        if _burst_data_type == BURST_DATA_TYPE['VOICE_HEAD']:
            if self.last_seq_id != _seq_id:
                self.last_seq_id = _seq_id
                self.call_start = time()
                self._logger.info('(%s) GROUP VOICE START: CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group))
                self._report.send_proxyEvent('({}) GROUP VOICE START: CallID: {} PEER: {}, SUB: {}, TS: {}, TGID: {}'.format(self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group)))
        
        # Action happens on un-key
        if _burst_data_type == BURST_DATA_TYPE['VOICE_TERM']:
            if self.last_seq_id == _seq_id:
                self.call_duration = time() - self.call_start
                self._logger.info('(%s) GROUP VOICE END:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s Duration: %.2fs', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group), self.call_duration)
                self._report.send_proxyEvent('({}) GROUP VOICE END:   CallID: {} PEER: {}, SUB: {}, TS: {}, TGID: {} Duration: {:.2f}s'.format(self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group), self.call_duration))
            else:
                self._logger.warning('(%s) GROUP VOICE END WITHOUT MATCHING START:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s', self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group),)
                self._report.send_proxyEvent('(%s) GROUP VOICE END WITHOUT MATCHING START:   CallID: %s PEER: %s, SUB: %s, TS: %s, TGID: %s'.format(self._system, int_id(_seq_id), int_id(_peerid), int_id(_src_sub), _ts, int_id(_dst_group)))


class proxyReportFactory(reportFactory):        
    def send_proxyEvent(self, _data):
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
    
    
    
    # PROXY.PY SPECIFIC ITEMS GO HERE:

    # Build the Access Control List
    ACL = build_acl('sub_acl')
    
    
    # MAIN INITIALIZATION ITEMS HERE
    
    # INITIALIZE THE REPORTING LOOP
    report_server = config_reports(CONFIG, logger, proxyReportFactory)
    
    # Build ID Aliases
    peer_ids, subscriber_ids, talkgroup_ids, local_ids = build_aliases(CONFIG, logger)
        
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGURED IPSC
    systems = mk_ipsc_systems(CONFIG, logger, systems, proxyIPSC, report_server)

  
  
    # INITIALIZATION COMPLETE -- START THE REACTOR
    reactor.run()
