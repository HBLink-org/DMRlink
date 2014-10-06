from __future__ import print_function
from pprint import pprint
from twisted.internet import reactor
from twisted.internet import task
from binascii import b2a_hex as h

import cPickle as pickle

import SimpleHTTPServer
import SocketServer


def int_id(_hex_string):
    return int(h(_hex_string), 16)

def print_stats(_request, _client_address, _server):
    stats_file = open('stats.py', 'r')
    NETWORK = pickle.load(stats_file)
    stats_file.close()
    for ipsc in NETWORK:
        print(ipsc)
        print('  MASTER Information:')
        print('    RADIO ID:               ', int_id(NETWORK[ipsc]['MASTER']['RADIO_ID']))
        print('      CONNECTED:            ', NETWORK[ipsc]['MASTER']['STATUS']['CONNECTED'])
        print('      KEEP ALIVES SENT:     ', NETWORK[ipsc]['MASTER']['STATUS']['KEEP_ALIVES_SENT'])
        print('      KEEP ALIVES RECEIVED: ', NETWORK[ipsc]['MASTER']['STATUS']['KEEP_ALIVES_RECEIVED'])
        print('      KEEP ALIVES MISSED:   ', NETWORK[ipsc]['MASTER']['STATUS']['KEEP_ALIVES_MISSED'])
        #pprint(NETWORK[ipsc]['MASTER']['STATUS'])

HTTP_PORT = 8080
HTTP_handler = print_stats
httpd = SocketServer.TCPServer(('', HTTP_PORT), HTTP_handler)
httpd.serve_forever()
    
output_stats = task.LoopingCall(print_stats)
output_stats.start(10)
reactor.run()