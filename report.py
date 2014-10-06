from pprint import pprint
from twisted.internet import reactor
from twisted.internet import task
import cPickle as pickle

def print_stats():
  stats_file = open('stats.py', 'r')
  NETWORK = pickle.load(stats_file)
  stats_file.close()
  pprint(NETWORK['C-BRIDGE'])
  
output_stats = task.LoopingCall(print_stats)
output_stats.start(10)
reactor.run()