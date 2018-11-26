#!/usr/bin/env python
#
###############################################################################
#   Copyright (C) 2016-2018  Cortney T. Buffington, N0MJS <n0mjs@me.com>
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

import ConfigParser
import sys

from socket import getaddrinfo, IPPROTO_UDP

# Does anybody read this stuff? There's a PEP somewhere that says I should do this.
__author__     = 'Cortney T. Buffington, N0MJS'
__copyright__  = 'Copyright (c) 2016-2018 Cortney T. Buffington, N0MJS and the K0USY Group'
__license__    = 'GNU GPLv3'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__      = 'n0mjs@me.com'


def get_address(_config):
    ipv4 = ''
    ipv6 = ''
    socket_info = getaddrinfo(_config, None, 0, 0, IPPROTO_UDP)
    for item in socket_info:
        if item[0] == 2:
            ipv4 = item[4][0]
        elif item[0] == 30:
            ipv6 = item[4][0]
        
    if ipv4:
        return ipv4
    if ipv6:
        return ipv6 
    return 'invalid address'

def build_config(_config_file):
    config = ConfigParser.ConfigParser()

    if not config.read(_config_file):
            sys.exit('Configuration file \''+_config_file+'\' is not a valid configuration file! Exiting...')        

    CONFIG = {}
    CONFIG['GLOBAL'] = {}
    CONFIG['REPORTS'] = {}
    CONFIG['LOGGER'] = {}
    CONFIG['ALIASES'] = {}
    CONFIG['SYSTEMS'] = {}    
    
    try:
        for section in config.sections():
            if section == 'GLOBAL':
                CONFIG['GLOBAL'].update({
                    'PATH': config.get(section, 'PATH')
                })

            elif section == 'REPORTS':
                CONFIG['REPORTS'].update({
                    'REPORT_NETWORKS': config.get(section, 'REPORT_NETWORKS'),
                    'REPORT_RCM': config.get(section, 'REPORT_RCM'),
                    'REPORT_INTERVAL': config.getint(section, 'REPORT_INTERVAL'),
                    'REPORT_PORT': config.get(section, 'REPORT_PORT'),
                    'REPORT_CLIENTS': config.get(section, 'REPORT_CLIENTS').split(','),
                    'PRINT_PEERS_INC_MODE': config.getboolean(section, 'PRINT_PEERS_INC_MODE'),
                    'PRINT_PEERS_INC_FLAGS': config.getboolean(section, 'PRINT_PEERS_INC_FLAGS')
                })
                if CONFIG['REPORTS']['REPORT_PORT']:
                    CONFIG['REPORTS']['REPORT_PORT'] = int(CONFIG['REPORTS']['REPORT_PORT'])
                if CONFIG['REPORTS']['REPORT_RCM']:
                    CONFIG['REPORTS']['REPORT_RCM'] = bool(CONFIG['REPORTS']['REPORT_RCM'])

            elif section == 'LOGGER':
                CONFIG['LOGGER'].update({
                    'LOG_FILE': config.get(section, 'LOG_FILE'),
                    'LOG_HANDLERS': config.get(section, 'LOG_HANDLERS'),
                    'LOG_LEVEL': config.get(section, 'LOG_LEVEL'),
                    'LOG_NAME': config.get(section, 'LOG_NAME')
                })
                
            elif section == 'ALIASES':
                CONFIG['ALIASES'].update({
                    'TRY_DOWNLOAD': config.getboolean(section, 'TRY_DOWNLOAD'),
                    'PATH': config.get(section, 'PATH'),
                    'PEER_FILE': config.get(section, 'PEER_FILE'),
                    'SUBSCRIBER_FILE': config.get(section, 'SUBSCRIBER_FILE'),
                    'TGID_FILE': config.get(section, 'TGID_FILE'),
                    'LOCAL_FILE': config.get(section, 'LOCAL_FILE'),
                    'PEER_URL': config.get(section, 'PEER_URL'),
                    'SUBSCRIBER_URL': config.get(section, 'SUBSCRIBER_URL'),
                    'STALE_TIME': config.getint(section, 'STALE_DAYS') * 86400,
                })
                
            elif config.getboolean(section, 'ENABLED'):
                CONFIG['SYSTEMS'].update({section: {'LOCAL': {}, 'MASTER': {}, 'PEERS': {}}})
                    
                CONFIG['SYSTEMS'][section]['LOCAL'].update({
                    # In case we want to keep config, but not actually connect to the network
                    'ENABLED':      config.getboolean(section, 'ENABLED'),
                
                    # These items are used to create the MODE byte
                    'PEER_OPER':    config.getboolean(section, 'PEER_OPER'),
                    'IPSC_MODE':    config.get(section, 'IPSC_MODE'),
                    'TS1_LINK':     config.getboolean(section, 'TS1_LINK'),
                    'TS2_LINK':     config.getboolean(section, 'TS2_LINK'),
                    'MODE': '',
                
                    # These items are used to create the multi-byte FLAGS field
                    'AUTH_ENABLED': config.getboolean(section, 'AUTH_ENABLED'),
                    'CSBK_CALL':    config.getboolean(section, 'CSBK_CALL'),
                    'RCM':          config.getboolean(section, 'RCM'),
                    'CON_APP':      config.getboolean(section, 'CON_APP'),
                    'XNL_CALL':     config.getboolean(section, 'XNL_CALL'),
                    'XNL_MASTER':   config.getboolean(section, 'XNL_MASTER'),
                    'DATA_CALL':    config.getboolean(section, 'DATA_CALL'),
                    'VOICE_CALL':   config.getboolean(section, 'VOICE_CALL'),
                    'MASTER_PEER':  config.getboolean(section, 'MASTER_PEER'),
                    'FLAGS': '',
                
                    # Things we need to know to connect and be a peer in this IPSC
                    'RADIO_ID':     hex(int(config.get(section, 'RADIO_ID')))[2:].rjust(8,'0').decode('hex'),
                    'IP':           config.get(section, 'IP'),
                    'PORT':         config.getint(section, 'PORT'),
                    'ALIVE_TIMER':  config.getint(section, 'ALIVE_TIMER'),
                    'MAX_MISSED':   config.getint(section, 'MAX_MISSED'),
                    'AUTH_KEY':     (config.get(section, 'AUTH_KEY').rjust(40,'0')).decode('hex'),
                    'GROUP_HANGTIME': config.getint(section, 'GROUP_HANGTIME'),
                    'NUM_PEERS': 0,
                    })
                # Master means things we need to know about the master peer of the network
                CONFIG['SYSTEMS'][section]['MASTER'].update({
                    'RADIO_ID': '\x00\x00\x00\x00',
                    'MODE': '\x00',
                    'MODE_DECODE': '',
                    'FLAGS': '\x00\x00\x00\x00',
                    'FLAGS_DECODE': '',
                    'STATUS': {
                        'CONNECTED':               False,
                        'PEER_LIST':               False,
                        'KEEP_ALIVES_SENT':        0,
                        'KEEP_ALIVES_MISSED':      0,
                        'KEEP_ALIVES_OUTSTANDING': 0,
                        'KEEP_ALIVES_RECEIVED':    0,
                        'KEEP_ALIVE_RX_TIME':      0
                        },
                    'IP': '',
                    'PORT': ''
                    })
                if not CONFIG['SYSTEMS'][section]['LOCAL']['MASTER_PEER']:
                    CONFIG['SYSTEMS'][section]['MASTER'].update({
                        'IP': get_address(config.get(section, 'MASTER_IP')),
                        'PORT': config.getint(section, 'MASTER_PORT')
                    })
            
                # Temporary locations for building MODE and FLAG data
                MODE_BYTE = 0
                FLAG_1 = 0
                FLAG_2 = 0
            
                # Construct and store the MODE field
                if CONFIG['SYSTEMS'][section]['LOCAL']['PEER_OPER']:
                    MODE_BYTE |= 1 << 6
                if CONFIG['SYSTEMS'][section]['LOCAL']['IPSC_MODE'] == 'ANALOG':
                    MODE_BYTE |= 1 << 4
                elif CONFIG['SYSTEMS'][section]['LOCAL']['IPSC_MODE'] == 'DIGITAL':
                    MODE_BYTE |= 1 << 5
                if CONFIG['SYSTEMS'][section]['LOCAL']['TS1_LINK']:
                    MODE_BYTE |= 1 << 3
                else:
                    MODE_BYTE |= 1 << 2
                if CONFIG['SYSTEMS'][section]['LOCAL']['TS2_LINK']:
                    MODE_BYTE |= 1 << 1
                else:
                    MODE_BYTE |= 1 << 0
                CONFIG['SYSTEMS'][section]['LOCAL']['MODE'] = chr(MODE_BYTE)

                # Construct and store the FLAGS field
                if CONFIG['SYSTEMS'][section]['LOCAL']['CSBK_CALL']:
                    FLAG_1 |= 1 << 7  
                if CONFIG['SYSTEMS'][section]['LOCAL']['RCM']:
                    FLAG_1 |= 1 << 6
                if CONFIG['SYSTEMS'][section]['LOCAL']['CON_APP']:
                    FLAG_1 |= 1 << 5
                if CONFIG['SYSTEMS'][section]['LOCAL']['XNL_CALL']:
                    FLAG_2 |= 1 << 7    
                if CONFIG['SYSTEMS'][section]['LOCAL']['XNL_CALL'] and CONFIG['SYSTEMS'][section]['LOCAL']['XNL_MASTER']:
                    FLAG_2 |= 1 << 6
                elif CONFIG['SYSTEMS'][section]['LOCAL']['XNL_CALL'] and not CONFIG['SYSTEMS'][section]['LOCAL']['XNL_MASTER']:
                    FLAG_2 |= 1 << 5
                if CONFIG['SYSTEMS'][section]['LOCAL']['AUTH_ENABLED']:
                    FLAG_2 |= 1 << 4
                if CONFIG['SYSTEMS'][section]['LOCAL']['DATA_CALL']:
                    FLAG_2 |= 1 << 3
                if CONFIG['SYSTEMS'][section]['LOCAL']['VOICE_CALL']:
                    FLAG_2 |= 1 << 2
                if CONFIG['SYSTEMS'][section]['LOCAL']['MASTER_PEER']:
                    FLAG_2 |= 1 << 0
                CONFIG['SYSTEMS'][section]['LOCAL']['FLAGS'] = '\x00\x00'+chr(FLAG_1)+chr(FLAG_2)
    
    except ConfigParser.Error, err:
        print(err)
        sys.exit('Could not parse configuration file, exiting...')
        
    return CONFIG


# Used to run this file direclty and print the config,
# which might be useful for debugging
if __name__ == '__main__':
    import sys
    import os
    import argparse
    from pprint import pprint
    
    # Change the current directory to the location of the application
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    # CLI argument parser - handles picking up the config file from the command line, and sending a "help" message
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action='store', dest='CONFIG_FILE', help='/full/path/to/config.file (usually dmrlink.cfg)')
    cli_args = parser.parse_args()


    # Ensure we have a path for the config file, if one wasn't specified, then use the execution directory
    if not cli_args.CONFIG_FILE:
        cli_args.CONFIG_FILE = os.path.dirname(os.path.abspath(__file__))+'/../dmrlink.cfg'
    
    
    pprint(build_config(cli_args.CONFIG_FILE))
