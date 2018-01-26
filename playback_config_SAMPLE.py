#!/usr/bin/env python
#
# THESE ARE THE THINGS THAT YOU NEED TO CONFIGURE TO USE playback.py

# ENABLE GROUP VOICE PLAYBACK?
#    Values may be True or False
GROUP_REPEAT = True
# TGID TO LISTEN FOR AND REPEAT ON
#    Integer for the Talkgroup ID
TGID = 12345
# TIMESLOT TO LISTEN FOR GROUP VOICE AND REPEAT
#    This is a tuple of timeslots to listen to. Note, if there's only
#    one, you still have to use the parenthesis and comma. Just
#    deal with it, or make it better. TS1 = 1, TS2 = 2.
GROUP_TS = (2,)
# ALTERNATE SOURCE SUBSCRIBER ID FOR REPEATED TRANSMISSION
#   Some folks have radios that don't respond to their own subscriber
#   IDs. Some just don't want to have the playback come from the same
#   subscriber ID. If this variable is set to something, it will
#   be used as the source subscriber for playback.
#       SET TO 0 TO NOT USE THIS FEATURE!!!
GROUP_SRC_SUB = 0


# ENABLE PRIVATE VOICE PLAYBACK?
#    Values may be True or False
PRIVATE_REPEAT = True
# SUBSCRIBER ID TO LISTEN FOR AND REPEAT ON
#    Integer for the Subscriber (Radio) ID
SUB = 12345
# TIMESLOT TO LISTEN FOR PRIVATE VOICE AND REPEAT
#    This is a tuple of timeslots to listen to. Note, if there's only
#    one, you still have to use the parenthesis and comma. Just
#    deal with it, or make it better. TS1 = 1, TS2 = 2.
PRIVATE_TS = (1,2)
