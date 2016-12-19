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

# This is a sample application that snoops voice traffic to log calls

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import time
from dmrlink import IPSC, systems
from dmr_utils.utils import hex_str_3, hex_str_4, int_id, get_alias

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK, Dave Kierzkowski, KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


class logIPSC(IPSC):
    def __init__(self, _name, _config, _logger):
        IPSC.__init__(self, _name, _config, _logger)
        self.ACTIVE_CALLS = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    
    def group_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        if (_ts not in self.ACTIVE_CALLS) or _end:
            _time       = time.strftime('%m/%d/%y %H:%M:%S')
            _dst_sub    = get_alias(_dst_sub, talkgroup_ids)
            _peerid     = get_alias(_peerid, peer_ids)
            _src_sub    = get_alias(_src_sub, subscriber_ids)
            if not _end:    self.ACTIVE_CALLS.append(_ts)
            if _end:        self.ACTIVE_CALLS.remove(_ts)
            if _end:    _end = 'END'
            else:       _end = 'START'
        
            print('{} ({}) Call {} Group Voice: \n\tIPSC Source:\t{}\n\tSubscriber:\t{}\n\tDestination:\t{}\n\tTimeslot\t{}' .format(_time, self._system, _end, _peerid, _src_sub, _dst_sub, _ts))

    def private_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        if (_ts not in self.ACTIVE_CALLS) or _end:
            _time       = time.strftime('%m/%d/%y %H:%M:%S')
            _dst_sub    = get_alias(_dst_sub, subscriber_ids)
            _peerid     = get_alias(_peerid, peer_ids)
            _src_sub    = get_alias(_src_sub, subscriber_ids)
            if not _end:    self.ACTIVE_CALLS.append(_ts)
            if _end:        self.ACTIVE_CALLS.remove(_ts)
        
            if _ts:     _ts = 2
            else:       _ts = 1
            if _end:    _end = 'END'
            else:       _end = 'START'
        
            print('{} ({}) Call {} Private Voice: \n\tIPSC Source:\t{}\n\tSubscriber:\t{}\n\tDestination:\t{}\n\tTimeslot\t{}' .format(_time, self._system, _end, _peerid, _src_sub, _dst_sub, _ts))
    
    def group_data(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        _dst_sub    = get_alias(_dst_sub, talkgroup_ids)
        _peerid     = get_alias(_peerid, peer_ids)
        _src_sub    = get_alias(_src_sub, subscriber_ids)
        print('({}) Group Data Packet Received From: {}' .format(self._system, _src_sub))
    
    def private_data(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):    
        _dst_sub    = get_alias(_dst_sub, subscriber_ids)
        _peerid     = get_alias(_peerid, peer_ids)
        _src_sub    = get_alias(_src_sub, subscriber_ids)
        print('({}) Private Data Packet Received From: {} To: {}' .format(self._system, _src_sub, _dst_sub))


if __name__ == '__main__':
    import argparse
    import os
    import sys
    import signal
    from dmr_utils.utils import try_download, mk_id_dict
    
    import dmrlink_log
    import dmrlink_config
    
    # Change the current directory to the location of the application
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    # CLI argument parser - handles picking up the config file from the command line, and sending a "help" message
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action='store', dest='CFG_FILE', help='/full/path/to/config.file (usually dmrlink.cfg)')
    cli_args = parser.parse_args()

    if not cli_args.CFG_FILE:
        cli_args.CFG_FILE = os.path.dirname(os.path.abspath(__file__))+'/dmrlink.cfg'
    
    # Call the external routine to build the configuration dictionary
    CONFIG = dmrlink_config.build_config(cli_args.CFG_FILE)
    
    # Call the external routing to start the system logger
    logger = dmrlink_log.config_logging(CONFIG['LOGGER'])

    logger.info('DMRlink \'log.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    
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
    
    
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGUED IPSC
    for system in CONFIG['SYSTEMS']:
        if CONFIG['SYSTEMS'][system]['LOCAL']['ENABLED']:
            systems[system] = logIPSC(system, CONFIG, logger)
            reactor.listenUDP(CONFIG['SYSTEMS'][system]['LOCAL']['PORT'], systems[system], interface=CONFIG['SYSTEMS'][system]['LOCAL']['IP'])
    
    reactor.run()