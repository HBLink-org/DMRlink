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
from os.path import getmtime 

__autdor__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2017 Cortney T. Buffington, N0MJS'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


# This is the only user-configuration necessary
#   Tell the program where the pickle file is
#   Tell the program where to write the html table file
#   Tell the program how often to print a report -- should match dmrlink report period
stat_file = '../confbridge_stats.pickle'
html_table_file = '../confbridge_stats.html'
frequency = 10

def read_dict():
    try:
        with open(stat_file, 'rb') as file:
            BRIDGES = load(file)
        return BRIDGES
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
    _now = time()
    _last_update = strftime('%Y-%m-%d %H:%M:%S', localtime(getmtime(stat_file)))
    _cnow = strftime('%Y-%m-%d %H:%M:%S', localtime(_now))
    BRIDGES = read_dict()
    if BRIDGES != 'None':
        
        stuff = 'Table Generated: {}<br>'.format(_cnow)
        stuff += 'Last Stat Data Recieved: {}<br>'.format(_last_update)
        
        #style="font: 10pt arial, sans-serif;"
        
        for bridge in BRIDGES:
            stuff += '<style>table, td, th {border: .5px solid black; padding: 2px; border-collapse: collapse}</style>'
            stuff += '<table style="width:90%; font: 10pt arial, sans-serif">'    
            stuff += '<colgroup>\
                <col style="width: 20%" />\
                <col style="width: 5%"  />\
                <col style="width: 5%"  />\
                <col style="width: 10%" />\
                <col style="width: 10%" />\
                <col style="width: 10%" />\
                <col style="width: 10%" />\
                <col style="width: 10%" />\
                <col style="width: 10%" />\
                </colgroup>'
            stuff += '<caption>{}</caption>'.format(bridge)
            stuff += '<tr><th>System</th>\
                          <th>Slot</th>\
                          <th>TGID</th>\
                          <th>Status</th>\
                          <th>Timeout</th>\
                          <th>Timeout Action</th>\
                          <th>ON Triggers</th>\
                          <th>OFF Triggers</th></tr>'
            
            
            for system in BRIDGES[bridge]:
                on = ''
                off = ''
                active = '<td bgcolor="#FFFF00">Unknown</td>'
                
                if system['TO_TYPE'] == 'ON' or system['TO_TYPE'] == 'OFF':
                    if system['TIMER'] - _now > 0:
                        exp_time = int(system['TIMER'] - _now)
                    else:
                        exp_time = 'Expired'
                    if system['TO_TYPE'] == 'ON':
                        to_action = 'Turn OFF'
                    else:
                        to_action = 'Turn ON'
                else:
                    exp_time = 'N/A'
                    to_action = 'None'
                
                if system['ACTIVE'] == True:
                    active = '<td bgcolor="#00FF00">Connected</td>'
                elif system['ACTIVE'] == False:
                    active = '<td bgcolor="#FF0000">Disconnected</td>'
                    
                for trigger in system['ON']:
                    on += str(int_id(trigger)) + ' '
                    
                for trigger in system['OFF']:
                    off += str(int_id(trigger)) + ' '

                stuff += '<tr> <td>{}</td> <td>{}</td> <td>{}</td> {} <td>{}</td> <td>{}</td> <td>{}</td> <td>{}</td> </tr>'.format(\
                        system['SYSTEM'],\
                        system['TS'],\
                        int_id(system['TGID']),\
                        active,\
                        exp_time,\
                        to_action,\
                        on,\
                        off)

            stuff += '</table><br>'
        
        write_file(stuff)


if __name__ == '__main__': 
    output_stats = task.LoopingCall(build_table)
    output_stats.start(frequency)
    reactor.run()