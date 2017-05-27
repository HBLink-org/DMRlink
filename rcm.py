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

# This is a sample application that uses the Repeater Call Monitor packets to display events in the IPSC
# NOTE: dmrlink.py MUST BE CONFIGURED TO CONNECT AS A "REPEATER CALL MONITOR" PEER!!!
# ALSO NOTE, I'M NOT DONE MAKING THIS WORK, SO UNTIL THIS MESSAGE IS GONE, DON'T EXPECT GREAT THINGS.

from __future__ import print_function
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as ahex

import datetime
import binascii
import dmrlink
import sys
from dmrlink import IPSC, mk_ipsc_systems, systems, reportFactory, build_aliases, config_reports
from dmr_utils.utils import get_alias, int_id
from ipsc.ipsc_const import *

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


status = True
rpt = True
nack = True

class rcmIPSC(IPSC):
    def __init__(self, _name, _config, _logger, _report):
        IPSC.__init__(self, _name, _config, _logger, _report)
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def call_mon_status(self, _data):
        if not status:
            return
        _source =   _data[1:5]
        _ipsc_src = _data[5:9]
        _seq_num =  _data[9:13]
        _ts =       _data[13]
        _status =   _data[15] # suspect [14:16] but nothing in leading byte?
        _rf_src =   _data[16:19]
        _rf_tgt =   _data[19:22]
        _type =     _data[22]
        _prio =     _data[23]
        _sec =      _data[24]
        
        _source = str(int_id(_source)) + ', ' + str(get_alias(_source, peer_ids))
        _ipsc_src = str(int_id(_ipsc_src)) + ', ' + str(get_alias(_ipsc_src, peer_ids))
        _rf_src = str(int_id(_rf_src)) + ', ' + str(get_alias(_rf_src, subscriber_ids))
        
        if _type == '\x4F' or '\x51':
            _rf_tgt = 'TGID: ' + str(int_id(_rf_tgt)) + ', ' + str(get_alias(_rf_tgt, talkgroup_ids))
        else:
            _rf_tgt = 'SID: ' + str(int_id(_rf_tgt)) + ', ' + str(get_alias(_rf_tgt, subscriber_ids))
        
        print('Call Monitor - Call Status')
        print('TIME:        ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print('DATA SOURCE: ', _source)
        print('IPSC:        ', self._system)
        print('IPSC Source: ', _ipsc_src)
        print('Timeslot:    ', TS[_ts])
        try:
            print('Status:      ', STATUS[_status])
        except KeyError:
            print('Status (unknown): ', ahex(_status))
        try:
            print('Type:        ', TYPE[_type])
        except KeyError:
            print('Type (unknown): ', ahex(_type))
        print('Source Sub:  ', _rf_src)
        print('Target Sub:  ', _rf_tgt)
        print()
    
    def call_mon_rpt(self, _data):
        if not rpt:
            return
        _source    = _data[1:5]
        _ts1_state = _data[5]
        _ts2_state = _data[6]
        
        _source = str(int_id(_source)) + ', ' + str(get_alias(_source, peer_ids))
        
        print('Call Monitor - Repeater State')
        print('TIME:         ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print('DATA SOURCE:  ', _source)
     
        try:
            print('TS1 State:    ', REPEAT[_ts1_state])
        except KeyError:
            print('TS1 State (unknown): ', ahex(_ts1_state))
        try:
            print('TS2 State:    ', REPEAT[_ts2_state])
        except KeyError:
            print('TS2 State (unknown): ', ahex(_ts2_state))
        print()
            
    def call_mon_nack(self, _data):
        if not nack:
            return
        _source = _data[1:5]
        _nack =   _data[5]
        
        _source = get_alias(_source, peer_ids)
        
        print('Call Monitor - Transmission NACK')
        print('TIME:        ', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print('DATA SOURCE: ', _source)
        try:
            print('NACK Cause:  ', NACK[_nack])
        except KeyError:
            print('NACK Cause (unknown): ', ahex(_nack))
        print()
    
    def repeater_wake_up(self, _data):
        _source = _data[1:5]
        _source_name = get_alias(_source, peer_ids)
        print('({}) Repeater Wake-Up Packet Received: {} ({})' .format(self._system, _source_name, int_id(_source)))


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
    report_server = config_reports(CONFIG, logger, reportFactory)
    
    # Build ID Aliases
    peer_ids, subscriber_ids, talkgroup_ids, local_ids = build_aliases(CONFIG, logger)
        
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGRUED IPSC
    systems = mk_ipsc_systems(CONFIG, logger, systems, rcmIPSC, report_server)



    # INITIALIZATION COMPLETE -- START THE REACTOR
    reactor.run()
