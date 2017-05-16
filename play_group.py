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

# This is a sample application that "plays" a voice tranmission from a file
# that was created with record.py. The file is just a pickle of an entire
# transmission.
# 
# This program consults a list of "trigger groups" for each timeslot that
# will initiate playback. When playback occurs, several items are re-written:
#   Source Subscriber: this DMRlink's local subscriber ID
#   Source Peer: this DMRlink's local subscriber ID
#   Timeslot: timeslot of the tranmission that triggered
#   TGID: TGID of the message that triggered it


from __future__ import print_function
from twisted.internet import reactor

import sys, time
import cPickle as pickle

from dmrlink import IPSC, mk_ipsc_systems, systems, reportFactory, build_aliases, config_reports

from dmr_utils.utils import int_id, hex_str_3
from ipsc.ipsc_const import BURST_DATA_TYPE

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2014 - 2015 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


# path+filename for the transmission to play back
filename = '../test.pickle'

# trigger logic - True, trigger on these IDs, False trigger on any but these IDs
trigger = True

# groups that we want to trigger playback of this file (ts1 and ts2)
#   Note this is a python list type, even if there's just one value
trigger_groups_1 = ['\x00\x00\x01', '\x00\x00\x0D', '\x00\x00\x64']
trigger_groups_2 = ['\x00\x0C\x30',]

class playIPSC(IPSC):
    def __init__(self, _name, _config, _logger,_report):
        IPSC.__init__(self, _name, _config, _logger, _report)
        self.CALL_DATA = []
        self.event_id = 1
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def group_voice(self, _src_sub, _dst_group, _ts, _end, _peerid, _data):
        if _end:
            _self_peer = self._config['LOCAL']['RADIO_ID']
            _self_src = _self_peer[1:]
            
            if (_peerid == _self_peer) or (_src_sub == _self_src):
                self._logger.error('(%s) Just received a packet that appears to have been originated by us. PeerID: %s Subscriber: %s TS: %s, TGID: %s', self._system, int_id(_peerid), int_id(_src_sub), int(_ts), int_id(_dst_group))
                return
            
            if trigger == False:
                if (_ts == 1 and _dst_group not in trigger_groups_1) or (_ts == 2 and _dst_group not in trigger_groups_2):
                    return
            else:
                if (_ts == 1 and _dst_group not in trigger_groups_1) or (_ts == 2 and _dst_group not in trigger_groups_2):
                    return
            
            self._logger.info('(%s) Event ID: %s - Playback triggered from SourceID: %s, TS: %s, TGID: %s, PeerID: %s', self._system, self.event_id, int_id(_src_sub), _ts, int_id(_dst_group), int_id(_peerid))
            
            # Determine the type of voice packet this is (see top of file for possible types)
            _burst_data_type = _data[30]
                
            time.sleep(2)
            self.CALL_DATA = pickle.load(open(filename, 'rb'))
            self._logger.info('(%s) Event ID: %s - Playing back file: %s', self._system, self.event_id, filename)
           
            for i in self.CALL_DATA:
                _tmp_data = i
                
                # re-Write the peer radio ID to that of this program
                _tmp_data = _tmp_data.replace(_peerid, _self_peer)
                # re-Write the source subscriber ID to that of this program
                _tmp_data = _tmp_data.replace(_src_sub, _self_src)
                # Re-Write the destination Group ID
                _tmp_data = _tmp_data.replace(_tmp_data[9:12], _dst_group)
                
                # Re-Write IPSC timeslot value
                _call_info = int_id(_tmp_data[17:18])
                if _ts == 1:
                    _call_info &= ~(1 << 5)
                elif _ts == 2:
                    _call_info |= 1 << 5
                _call_info = chr(_call_info)
                _tmp_data = _tmp_data[:17] + _call_info + _tmp_data[18:]
                    
                # Re-Write DMR timeslot value
                # Determine if the slot is present, so we can translate if need be
                if _burst_data_type == BURST_DATA_TYPE['SLOT1_VOICE'] or _burst_data_type == BURST_DATA_TYPE['SLOT2_VOICE']:
                    # Re-Write timeslot if necessary...
                    if _ts == 1:
                        _burst_data_type = BURST_DATA_TYPE['SLOT1_VOICE']
                    elif _ts == 2:
                        _burst_data_type = BURST_DATA_TYPE['SLOT2_VOICE']
                    _tmp_data = _tmp_data[:30] + _burst_data_type + _tmp_data[31:]

                # Send the packet to all peers in the target IPSC
                self.send_to_ipsc(_tmp_data)
                time.sleep(0.06)
            self.CALL_DATA = []
            self._logger.info('(%s) Event ID: %s - Playback Completed', self._system, self.event_id)
            self.event_id = self.event_id + 1
        

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
    systems = mk_ipsc_systems(CONFIG, logger, systems, playIPSC, report_server)



    # INITIALIZATION COMPLETE -- START THE REACTOR
    reactor.run()