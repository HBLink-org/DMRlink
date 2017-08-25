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

#************************************
# WHAT THIS PROGRAM WILL DO
#************************************
'''
This program will log RCM 'status' messages to a MySQL database, based on
the DB configuration information supplied in the section labelled
"USER DEFINED ITEMS GO HERE". Columns logged are as follows:
    data_source (INT) - The DMR radio ID of the source of this information
    ipsc (INT)        - The IPSC peer that was the origin of the event that triggered this message
    timeslot (INT)    - IPSC timeslot, 0 if not applicable
    type (VARCHAR)    - The type of radio call, if applicable
    subscriber (INT)  - the RF source, if applicable, that caused the message
    talkgroup (INT)   - the TGID, if applicable
    status (VARCHAR)  - the RCM message time for 'status' messages
'''

from __future__ import print_function
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task

import pymysql
import dmrlink
from dmrlink import IPSC, mk_ipsc_systems, systems, reportFactory, build_aliases, config_reports

from ipsc.ipsc_const import *

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski KD8EYF and he who wishes not to be named'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


#************************************
# USER DEFINED ITEMS GO HERE
#************************************
#
db_host  = '127.0.0.1'
db_port  = 1234
db_user  = 'dmrlink'
db_pwd   = 'dmrlink'
db_name  = 'dmrlink'
# 
# To change the table name, look for the line with:
#   cur.execute("insert INTO rcm_status(da...
# and change "rcm_status" to the name of your table
#
#************************************


class rcmIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def call_mon_status(self, _network, _data):
        _source   = int_id(_data[1:5])
        _ipsc_src = int_id(_data[5:9])
        _ts       = TS[_data[13]]
        _status   = _data[15] # suspect [14:16] but nothing in leading byte?
        _rf_src   = int_id(_data[16:19])
        _rf_tgt   = int_id(_data[19:22])
        _type     = _data[22]

        try:
            _status = STATUS[_status]
        except KeyError:
            pass
        try:
            _type = TYPE[_type]
        except KeyError:
            pass
            
        con = pymysql.connect(host = db_host, port = db_port, user = db_user, passwd = db_pwd, db = db_name)
        cur = con.cursor()
        cur.execute("insert INTO rcm_status(data_source, ipsc, timeslot, type, subscriber, talkgroup, status) VALUES(%s, %s, %s, %s, %s, %s, %s)", (_source, _ipsc_src, _ts, _type, _rf_src, _rf_tgt, _status))
        con.commit()
        con.close()


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