# Copyright (c) 2013 - 2015 Cortney T. Buffington, N0MJS and the K0USY Group. n0mjs@me.com
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# Known IPSC Message Types
CALL_CONFIRMATION     = '\x05' # Confirmation FROM the recipient of a confirmed call.
TXT_MESSAGE_ACK       = '\x54' # Doesn't seem to mean success, though. This code is sent success or failure
CALL_MON_STATUS       = '\x61' #  |
CALL_MON_RPT          = '\x62' #  | Exact meaning unknown
CALL_MON_NACK         = '\x63' #  |
XCMP_XNL              = '\x70' # XCMP/XNL control message
GROUP_VOICE           = '\x80'
PVT_VOICE             = '\x81'
GROUP_DATA            = '\x83'
PVT_DATA              = '\x84'
RPT_WAKE_UP           = '\x85' # Similar to OTA DMR "wake up"
UNKNOWN_COLLISION     = '\x86' # Seen when two dmrlinks try to transmit at once
MASTER_REG_REQ        = '\x90' # FROM peer TO master
MASTER_REG_REPLY      = '\x91' # FROM master TO peer
PEER_LIST_REQ         = '\x92' # From peer TO master
PEER_LIST_REPLY       = '\x93' # From master TO peer
PEER_REG_REQ          = '\x94' # Peer registration request
PEER_REG_REPLY        = '\x95' # Peer registration reply
MASTER_ALIVE_REQ      = '\x96' # FROM peer TO master
MASTER_ALIVE_REPLY    = '\x97' # FROM master TO peer
PEER_ALIVE_REQ        = '\x98' # Peer keep alive request
PEER_ALIVE_REPLY      = '\x99' # Peer keep alive reply
DE_REG_REQ            = '\x9A' # Request de-registration from system
DE_REG_REPLY          = '\x9B' # De-registration reply

# IPSC Version Information
IPSC_VER_14           = '\x00'
IPSC_VER_15           = '\x00'
IPSC_VER_15A          = '\x00'
IPSC_VER_16           = '\x01'
IPSC_VER_17           = '\x02'
IPSC_VER_18           = '\x02'
IPSC_VER_19           = '\x03'
IPSC_VER_22           = '\x04'

# Link Type Values - assumed that cap+, etc. are different, this is all I can confirm
LINK_TYPE_IPSC        = '\x04'

# Burst Data Types
BURST_DATA_TYPE = {
    'VOICE_HEAD':  '\x01',
    'VOICE_TERM':  '\x02',
    'SLOT1_VOICE': '\x0A',
    'SLOT2_VOICE': '\x8A'   
}

# IPSC Version and Link Type are Used for a 4-byte version field in registration packets
IPSC_VER              = LINK_TYPE_IPSC + IPSC_VER_17 + LINK_TYPE_IPSC + IPSC_VER_16

# Packets that must originate from a peer (or master peer)
ANY_PEER_REQUIRED = [GROUP_VOICE, PVT_VOICE, GROUP_DATA, PVT_DATA, CALL_MON_STATUS, CALL_MON_RPT, CALL_MON_NACK, XCMP_XNL, RPT_WAKE_UP, DE_REG_REQ]

# Packets that must originate from a non-master peer
PEER_REQUIRED = [PEER_ALIVE_REQ, PEER_ALIVE_REPLY, PEER_REG_REQ, PEER_REG_REPLY]

# Packets that must originate from a master peer
MASTER_REQUIRED = [PEER_LIST_REPLY, MASTER_ALIVE_REPLY]

# User-Generated Packet Types
USER_PACKETS = [GROUP_VOICE, PVT_VOICE, GROUP_DATA, PVT_DATA]

# RCM (Repeater Call Monitor) Constants

TS = {
    '\x00': '1',
    '\x01': '2'
}

NACK = {
    '\x05': 'BSID Start',
    '\x06': 'BSID End'
}

TYPE = {
    '\x30': 'Private Data Set-Up',
    '\x31': 'Group Data Set-Up',
    '\x32': 'Private CSBK Set-Up',
    '\x45': 'Call Alert',
    '\x47': 'Radio Check Request',
    '\x48': 'Radio Check Success',
    '\x49': 'Radio Disable Request',
    '\x4A': 'Radio Disable Received',
    '\x4B': 'Radio Enable Request',
    '\x4C': 'Radio Enable Received',
    '\x4D': 'Remote Monitor Request',
    '\x4E': 'Remote Monitor Request Received', #(doesn't mean it was successful) 
    '\x4D': 'Remote Monitor Request',
    '\x4F': 'Group Voice',
    '\x50': 'Private Voice',
    '\x51': 'Group Data',
    '\x52': 'Private Data',
    '\x53': 'All Call',
    '\x54': 'Message ACK/Failure', #text message acknowledgement, but doesn't mean it was successful - it gives the same code if it worked or failed...
    '\x84': 'ARS/GPS?' # Not yet clear, seen by a user running ARS & GPS
}

SEC = {
    '\x00': 'None',
    '\x01': 'Basic',
    '\x02': 'Enhanced'
}

STATUS = {
    '\x01': 'Active',
    '\x02': 'End',
    '\x05': 'TS In Use',
    '\x08': 'RPT Disabled',
    '\x09': 'RF Interference',
    '\x0A': 'BSID ON',
    '\x0B': 'Timeout',
    '\x0C': 'TX Interrupt'
}

REPEAT = {
    '\x01': 'Repeating',
    '\x02': 'Idle',
    '\x03': 'TS Disabled',
    '\x04': 'TS Enabled'
}


# DMR IPSC Contants (in the RTP Payload)

BURST_DATA_TYPE = {
    'VOICE_HEAD':  '\x01',
    'VOICE_TERM':  '\x02',
    'SLOT1_VOICE': '\x0A',
    'SLOT2_VOICE': '\x8A'   
}
