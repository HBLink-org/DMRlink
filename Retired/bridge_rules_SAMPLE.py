'''
The following is an example for your bridge_rules file. Note, all bridging is ONE-WAY!
Rules for an IPSC network indicate destination IPSC network for the Group ID specified
(allowing transcoding of the Group ID to a different value). Group IDs used to be 
hex strings, then a function was added to convert them, now that function has been
moved into the bridge.py (program file) to make this file as simple and easy as
possible

The IPSC name must match an IPSC name from dmrlink.cfg, and any IPSC network defined
as "active" in the dmrlink.cfg *MUST* have an entry here. It may be an empty entry,
but there must be one so that the data structure can be parsed.

The example below cross-patches TS 1/TGID 1 on an IPSC network named "IPSC_FOO" with 
TS 2/TGID 2 on an IPSC network named "IPSC_BAR". Note, one entry must be made on EACH
IPSC network (IPSC_FOO and IPSC_BAR in this example) for bridging to occur in both
directions.

THIS EXAMPLE WILL NOT WORK AS IT IS - YOU MUST SPECIFY NAMES AND GROUP IDS!!!

NOTES:
    * PRIVATE_VOICE is not yet implemented
    * GROUP_HANGTIME should be set to the same value as the repeaters in the IPSC network
    * TRUNK is a boolean set to True only for DMRlink to DMRlink IPSCs that need to move 
        multiple packet streams that may match the same TS - this essentially makes the
        source,timeslot,talkgroup ID a tuple to indentify an arbitrary number of streams
    * NAME is any name you want, and is used to match reciprocal rules for user-activateion
    * ACTIVE should be set to True if you want the rule active by default, False to be inactive
    * ON and OFF are LISTS of Talkgroup IDs used to trigger this rule off and on. Even if you
        only want one (as shown in the ON example), it has to be in list format. None can be
        handled with an empty list, such as " 'ON': [] ".
    * TO_TYPE is timeout type. If you want to use timers, ON means when it's turned on, it will
        turn off afer the timout period and OFF means it will turn back on after the timout
        period. If you don't want to use timers, set it to anything else, but 'NONE' might be
        a good value for documentation!
    * TIMOUT is a value in minutes for the timout timer. No, I won't make it 'seconds', so don't
        ask. Timers are performance "expense".

DO YOU THINK THIS FILE IS TOO COMPLICATED?
    Because you guys all want more and more features, this file is getting complicated. I have
    dabbled with using a parser to make it easier to build. I'm torn. There is a HUGE benefit
    to having it like it is. This is a python file. Simply running it
    (i.e. "python bridge_rules.py) will tell you if there's a syntax error and where. Think
    about that for a few minutes :)
'''

RULES = {
    'IPSC_FOO': {
        'TRUNK': False,
        'GROUP_HANGTIME': 5,
        'GROUP_VOICE': [
            {'NAME': 'STATEWIDE', 'ACTIVE': False, 'TO_TYPE': 'ON', 'TIMEOUT': 2, 'ON': [8,], 'OFF': [9,10], 'SRC_TS': 1, 'SRC_GROUP': 1, 'DST_NET': 'IPSC_BAR', 'DST_TS': 2, 'DST_GROUP': 2},
            # Send the IPSC_FOO network Time Slice 1, Talk Group 1 to the IPSC_BAR network on Time Slice 2 Talk Group 2
            # Repeat the above line for as many rules for this IPSC network as you want.
        ],
        'PRIVATE_VOICE': [
        ]
    },
    'IPSC_BAR': {
        'TRUNK': False,
        'GROUP_HANGTIME': 5,
        'GROUP_VOICE': [
            {'NAME': 'STATEWIDE', 'ACTIVE': False, 'TO_TYPE': 'ON', 'TIMEOUT': 2, 'ON': [8,], 'OFF': [9,10], 'SRC_TS': 2, 'SRC_GROUP': 2, 'DST_NET': 'IPSC_FOO', 'DST_TS': 1, 'DST_GROUP': 1},
            # Send the IPSC_BAR network Time Slice 2, Talk Group 2 to the IPSC_FOO network on Time Slice 1 Talk Group 1
            # Repeat the above line for as many rules for this IPSC network as you want.
        ],
        'PRIVATE_VOICE': [
        ]
    }
}
