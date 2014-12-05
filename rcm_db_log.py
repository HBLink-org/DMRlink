#!/usr/bin/env python
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

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
from dmrlink import IPSC, NETWORK, networks, get_info, int_id, logger

__author__ = 'Cortney T. Buffington, N0MJS'
__copyright__ = 'Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__ = 'Adam Fast, KC0YLK, Dave K, and he who wishes not to be named'
__license__ = 'Creative Commons Attribution-ShareAlike 3.0 Unported'
__version__ = '1.0'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__ = 'n0mjs@me.com'
__status__ = 'Beta'

#************************************
# USER DEFINED ITEMS GO HERE
#************************************
#
db_host  = '127.0.0.1'
db_port  = 8889
db_user  = 'dmrlink'
db_pwd   = 'k0usy'
db_name  = 'dmrlink'
# 
# To change the table name, look for the line with:
#   cur.execute("insert INTO rcm_status(da...
# and change "rcm_status" to the name of your table
#
#************************************

try:
    from ipsc.ipsc_message_types import *
except ImportError:
    sys.exit('IPSC message types file not found or invalid')

class rcmIPSC(IPSC):
    
    def __init__(self, *args, **kwargs):
        IPSC.__init__(self, *args, **kwargs)
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    def call_mon_status(self, _network, _data):
        _source =   int_id(_data[1:5])
        _ipsc_src = int_id(_data[5:9])
        _ts =       TS[_data[13]]
        _status =   _data[15] # suspect [14:16] but nothing in leading byte?
        _rf_src =   int_id(_data[16:19])
        _rf_tgt =   int_id(_data[19:22])
        _type =     _data[22]

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
    logger.info('DMRlink \'rcm_db_log.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    for ipsc_network in NETWORK:
        if NETWORK[ipsc_network]['LOCAL']['ENABLED']:
            networks[ipsc_network] = rcmIPSC(ipsc_network)
            reactor.listenUDP(NETWORK[ipsc_network]['LOCAL']['PORT'], networks[ipsc_network], interface=NETWORK[ipsc_network]['LOCAL']['IP'])
    reactor.run()