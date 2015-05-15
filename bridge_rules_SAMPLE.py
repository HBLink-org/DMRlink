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
'''

RULES = {
    'IPSC_FOO': {
        'GROUP_HANGTIME': 5,
        'GROUP_VOICE': [
            {'SRC_GROUP': 1, 'SRC_TS': 1, 'DST_NET': 'IPSC_BAR', 'DST_GROUP': 2, 'DST_TS': 2},
            # Repeat the above line for as many rules for this IPSC network as you want.
        ],
        'PRIVATE_VOICE': [
        ]
    },
    'IPSC_BAR': {
        'GROUP_HANGTIME': 5,
        'GROUP_VOICE': [
            {'SRC_GROUP': 2, 'SRC_TS': 2, 'DST_NET': 'IPSC_FOO', 'DST_GROUP': 1, 'DST_TS': 1},
            # Repeat the above line for as many rules for this IPSC network as you want.
        ],
        'PRIVATE_VOICE': [
        ]
    }
}
