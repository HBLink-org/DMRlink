'''
WARNING - IF YOU USE THIS FILE, BRIDGE.PY WILL ASSUME IT IS TO
OPERATE IN BACKUP BRIDGE MODE. THIS MAY REALLY RUIN YOUR DAY!

The following is an example for your "known_bridges" file. This is a
simple list (in python syntax) of integer DMR radios IDs of bridges
that we expect to encounter.

You should only add bridges that will be encountered - adding a bunch
of bridges just because you can will really slow things down, so don't
do it. Please note each line but the last must end in a comma. This is
about the only thing you can mess up... but I manage to bork that one
every 3rd time or so I make updates, so watch out.

A bridge that is "encountered" means another bridge that might be in
the same IPSC network we're going to try to bridge for. This is useful
only in the case where we want to provide backup bridging service.
There are cases when you do NOT want to use this feature -- say for 
example if one IPSC has two bridges but they're bridging different
talkgroups.
'''

BRIDGES = [
    123456,
    234567,
    345678
    ]
    
    