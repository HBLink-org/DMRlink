#!/usr/bin/env python
#
###############################################################################
#   Copyright (C) 2017  Cortney T. Buffington, N0MJS <n0mjs@me.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of tde GNU General Public License as published by
#   the Free Software Foundation; eitder version 3 of the License, or
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

from __future__ import print_function
from cPickle import load
from pprint import pprint
from time import time, strftime, localtime
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h
from dmr_utils.utils import int_id, get_alias

__autdor__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2017 Cortney T. Buffington, N0MJS'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


# This is the only user-configuration necessary
#   Tell the program where the pickle file is
#   Tell the program where to write the html table file
#   Tell the program how often to print a report -- should match dmrlink report period
stat_file = '../dmrlink_stats.pickle'
html_table_file = '../stats.html'
frequency = 30

def read_dict():
    try:
        with open(stat_file, 'rb') as file:
            NETWORK = load(file)
        return NETWORK
    except IOError as detail:
        print('I/O Error: {}'.format(detail))
    except EOFError:
        print('EOFError')
        
def write_file(_string):
    try:
        with open(html_table_file, 'w') as file:
            file.write(_string)
            file.close()
    except IOError as detail:
        print('I/O Error: {}'.format(detail))
    except EOFError:
        print('EOFError')
            
def build_table():
    NETWORK = read_dict()
    if NETWORK != 'None':
        _cnow = strftime('%Y-%m-%d %H:%M:%S', localtime(time()))
        stuff = 'Last Update: {}'.format(_cnow)
        stuff += '<style>table, td, th {border: .5px solid black; padding: 2px; border-collapse: collapse}</style>'
        
        for ipsc in NETWORK:
            stat = NETWORK[ipsc]['MASTER']['STATUS']
            master = NETWORK[ipsc]['LOCAL']['MASTER_PEER']
            
            stuff += '<table style="width:90%; font: 10pt arial, sans-serif">'
            
            stuff += '<colgroup>\
                <col style="width: 10%" />\
                <col style="width: 20%" />\
                <col style="width: 20%" />\
                <col style="width: 10%" />\
                <col style="width: 15%" />\
                <col style="width: 15%" />\
                <col style="width: 10%" />\
                </colgroup>'
            
            stuff += '<caption>{} '.format(ipsc)
            if master:
                stuff += '(master)'
            else:
                stuff += '(peer)'
            stuff +='</caption>'
            
            stuff += '<tr><th rowspan="2">Type</th>\
                    <th rowspan="2">Radio ID</th>\
                    <th rowspan="2">IP Address</th>\
                    <th rowspan="2">Connected</th>\
                    <th colspan="3">Keep Alives</th></tr>\
                    <tr><th>Sent</th><th>Received</th><th>Missed</th></tr>'
                    
            if not master:
                stuff += '<tr><td>Master</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(\
                        str(int_id(NETWORK[ipsc]['MASTER']['RADIO_ID'])).rjust(8,'0'),\
                        NETWORK[ipsc]['MASTER']['IP'],\
                        stat['CONNECTED'],\
                        stat['KEEP_ALIVES_SENT'],\
                        stat['KEEP_ALIVES_RECEIVED'],\
                        stat['KEEP_ALIVES_MISSED'],)
        
            if master:
                for peer in NETWORK[ipsc]['PEERS']:
                    stat = NETWORK[ipsc]['PEERS'][peer]['STATUS']
                    stuff += '<tr><td>Peer</td><td>{}</td><td>{}</td><td>{}</td><td>n/a</td><td>{}</td><td>n/a</td></tr>'.format(\
                        str(int_id(peer)).rjust(8,'0'),\
                        NETWORK[ipsc]['PEERS'][peer]['IP'],\
                        stat['CONNECTED'],\
                        stat['KEEP_ALIVES_RECEIVED'])
                    
            else:
                for peer in NETWORK[ipsc]['PEERS']:
                    stat = NETWORK[ipsc]['PEERS'][peer]['STATUS']
                    if peer != NETWORK[ipsc]['LOCAL']['RADIO_ID']:
                        stuff += '<tr><td>Peer</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(\
                            str(int_id(peer)).rjust(8,'0'),\
                            NETWORK[ipsc]['PEERS'][peer]['IP'],\
                            stat['CONNECTED'],\
                            stat['KEEP_ALIVES_SENT'],\
                            stat['KEEP_ALIVES_RECEIVED'],\
                            stat['KEEP_ALIVES_MISSED'])
            stuff += '</table><br>'
        
        write_file(stuff)


if __name__ == '__main__': 
    output_stats = task.LoopingCall(build_table)
    output_stats.start(frequency)
    reactor.run()