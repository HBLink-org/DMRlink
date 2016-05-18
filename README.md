#NOTICE: The only licensing stipulation for DMRlink is to provide attribution. Come on guys, start providing attribution as required by the license, and outlined in this document or DMRlink is going to be taken down. ONE SIMPLE RULE and NONE of you have followed it.#


**FOR THE IMPATENT PLEASE AT LEAST READ THIS**

There are two ways to "install" DMRlink:

1) Use the Makefile

2) Don't

The makefile will create a directory tree and copy all of the pertient files, making duplicates of some things so that each of the applications have a full set of all of the files they need, standalone.

Not using the makefile leaves the structure as it existis in the repo, which is fully functional. It trades the autonomy of the file tree and duplicates for a simpler installation, and the ability to sync to new versions more easily.

The one you use is up to you -- just please don't blindly go download it and type "make" becuase that's just what you always do. Please think about it.


##PROJECT: Open Source IPSC Client.
**PURPOSE:** Understanding IPSC, building an open-source IPSC "stack", troubleshooting IPSC performance issues, and as a basis to easily write applications such as logging, bridging, etc.

**IMPACT:** Potential concern from Motorla Solutions, as IPSC is a proprietary protocol.

**METHOD:** Reverse engineering by pattern matching and process of elimination.
  
**PROPERTY:**  
This work represents the author's interpretation of the Motorola(tm) MOTOTRBO(tm) IPSC protocol. It is intended for academic purposes and not for commercial gain. It is not guaranteed to work, or be useful in any way, though it is intended to help IPSC users better understand, and thus maintain and operate, IPSC networks. This work is not affiliated with Motorola Solutions(tm), Inc. in any way. Motorola, Motorola Solutions, MOTOTRBO, ISPC and other terms in this document are registered trademarks of Motorola Solutions, Inc. Other registered trademark terms may be used. These are owned and held by their respective owners.  
  
**PRE-REQUISITE KNOWLEDGE:**  
This document assumes the reader is familiar with the concepts presented in the Motorola Solutions(tm), Inc. MOTOTRBO(tm) Systems Planner.  
  
**CONVENTIONS USED:**  
When communications exchanges are described, the symbols "->" and "<-" are used to denote the *direction* of the communcation. For example, "PEER -> MASTER" indicates communcation from the peer to the master. For each exchange outlined, the initiator of the particular communication will be on the left for the duration of the particular item being illustrated.

**HOW TO USE THIS SOFTWARE:**  
The primary objective is the IPSC "stack" itself, and is represended in dmrlink.py. It gets the majority of work, and the applicaitons are examples to show how dmrlink.py can be used. As such, dmrlink.py, dmrlink.cfg and the ipsc directory are pre-requisites for eveyrthing here. dmrlink.py does very little on it's own, but you should ALWAYS make sure it runs directly, as nothing else will work if it does not. Turn on the logging options, set the logger to DEBUG and watch to make sure everything works right **BEFORE** working with the application files.

dmrlink, optionally, uses three additional files to map DMR identifiers to understandable names. These are the .csv files for subscribers, peers (other repeaters, 3rd party console applications, etc.) and one for common talkgroups. These files are really only meaningful for logging and reporting.

The remaining files are sample applicaitons that sub-class dmrlink. Since dmrlink takes a default action on each packet type, overriding the class methods for particular packet types are how the examples are presented. For example, bridge.py only needs access to group voice packets, so the group_voice class method is overridden to perform the bridging function. In this particlar example, several other class methods are also overridden, but only to set them to do nothing.

**FILES:**  
+ ***dmrlink.py, dmrlink.cfg, ipsc (directory):*** Core files for dmrlink to work
+ ***talkgroup_ids.csv, subscriber_ids.csv, peer_ids.csv:*** DMR numeric ID to name mapping files (optional)
+ ***bridge.py, log.py, rcm.py, playback.py, playback.py, play_group.py, record.py:*** Sample applications to demonstrate dmrlink's abilities
+ ***files with SAMPLE in the name:*** Configuration files for certain apps - remove "_SAMPLE" and customize to your needs to use. for example, "dmrlink_SAMPLE.cfg" becomes "dmrlink.cfg"

**SAMPLE APPLICATIONS:**

***bridge.py:*** This applicaiton allows DMRlink to function as an IPSC bridge. Bridging means connecting multiple IPSC networks together, and allowing only certain timeslot/group IDs, etc. to pass between them. Sometimes re-writing the talkgroup ID, etc. bridge.py does not have nearly the wealth of features that commercial IPSC bridges do, but works very, very well. One unique feature here is that bridge.py can be told the radio ID of other bridges and can operate in multiple bridge active/standby/standby... configurations -- which is to say, you may have TWO bridges configured in the same IPSC, set to bridge the same talkgroups, but only one will be active at a time, offering multiple-bridge redundancy to minimize service outages. When two or more instances of DMRlink are connected to each other, and they are the ONLY devices in the IPSC, you may trunk many more than 2 packet streams at once between them.

***log.py:*** This is a logging application based on gathering data from the actual call packet stream. It doesn't do a whole awful lot, but it is an example of the IPSC side of building a back-end data gathering applicaiton without screen-scraping or tcpdumping a c-Bridge, etc. As a sample app, it just logs to the screen, or a file, etc. but it would be trivial to have it log to a database for web presentation, a central syslog server, etc.

***rcm.py:*** Very similar to log.py, but this one uses a feature called "Repeater Call Monitor" to get nearly identical data, but puts a MUCH smaller load on the IPSC network, since user call datastreams aren't forwarded to DMRlink running as (and properly configured as) an RCM. All of the logging, almost none of the overhead. Again, beats the pants off of screen-scraping, tcpdumping, etc.

***playback.py:*** As of this writing, a large multi-national ham radio group has deployed this on TGID 9998 and dubbed it the "parrot". This application can listen to group and/or private voice transmissions and if you trasmit to the group and/or private IDs it's programmed to use, it will record the digital packet stream and then re-play it back. Handy for listening to your audio to see what you actually sound like on the air.

***play_group.py:*** NOT YET STABLE. This applicaiton is for playing back pre-recorded audio messages based on particlar events. Events could be IPSC-based (like a keyup on a particular TS/TGID combination, time of day, etc.). It works, but requires quite a bit of under-the-hood mucking about as of now.

***record.py:*** Companion applicaiton to play_group.py. This will never be "fancy", since it's intended as a utility for network operators to use to capture voice call packet streams to be played back later. It will be improved beyond where it is at now, but not a high priority.


**CONFIGURATION:**

The configuration file for dmrlink is in ".ini" format, and is self-documented. A warning not in the self-documentation: Don't enable features you do not undertand, it can break dmrlink or the target IPSC (nothing turning off dmrlink shouldn't fix). There are options avaialble because the IPSC protocol appears to make them available, but dmrlink doesn't yet understand them. For exmaple, dmrlink does not process XNL/XCMP. If you enable it, and other peers expect interaction with it, the results may be unpredictable. Chances are, you'll confuse applications like RDAC that require it. The advantage to dmrlink not processing XNL/XCMP is that it also cannot "brick" a repeater or subscriber, since all of these dangerous features use XNL/XCMP.
  
###CONNECTION ESTABLISHMENT AND MAINTENANCE

**CORE CONCEPTS:**  
The IPSC system contains, essentially, two types of nodes: Master and Peer. Each IPSC network has exactly one master device and zero or more peers, recommended not to exceed 15. IPSC nodes may be a number of types of systems, such as repeaters, dispatch consoles, application software, etc. For example, the Motorola RDAC application acts as a peer in the IPSC network, though it doesn't operate as a repeater. The IPSC protocol supports many possible node types, and only a few have been identified. This document currently only explores repeaters - both Master and Peer, and their roles in the IPSC network.  
  
All IPSC communication is via UDP, and only the master needs a static IP address. Masters will operate behind NATs. A single UDP port, specified in programming the IPSC master device must be mapped through any NAT/stateful firewalls for the master, while peers require no special treatment.  
  
All nodes in an IPSC network maintain communication with each other at all times. The role of the master is merely to coordinate the joining of new nodes to the IPSC network. A functional IPSC network will continue without its master, as long as no new nodes need to join (or existing nodes need to re-join after a communications outage, etc.) This is one of the most important core concepts in IPSC, as it is central to the NAT traversal AND tracking of active peers.  
  
Each peer will send keep-alives to each other peer in the IPSC network at an interval specified in the devices "firewall open timer". The elegantly simple, yet effective approach of IPSC, uses this keep-alive to both open, and keep open stateful firewall and NAT translations between peers. Since each device handles all communications from a single UDP port, when a device sends a keep-alive or a registration request to another device, the source-destination address/port tuple for that communication is opened through stateful devices. The only requirement to maintain communication is that this timer be shorter than the UDP session timeout of network control elements (firewalls, packet shapers, NATs, etc.) Moreover, it does NOT appear that all devices in the IPSC network require the same setting for this. Each device would appear to maintain its own set timing without interference from different interval settings on other nodes in the IPSC.  
  
**KNOWN IPSC PACKET TYPES:**  
The following sections of this document will include various packet types. This is a list of currently known types and their meanings. Note: The names are arbitrarily chosen with the intention of being descriptive, and each is defined by what they've been "observed" to do in the wild.  

	CALL_CONFIRMATION         = 0x05        Confirmation FROM the recipient of a confirmed call.
    CALL_MON_ORIGIN           = 0x61        Sent to Repeater Call Monitor Peers from repeater originating a call
	CALL_MON_RPT              = 0x62        Sent to Repeater Call Monitor Peers from all repeaters repeating a call
	CALL_MON_NACK             = 0x63        Sent to Repeater Call Monitor Peers from repeaters that cannot transmit a call (ie. ID in progress)
	XCMP_XNL         		  = 0x70		Control protocol messages
	GROUP_VOICE      		  = 0x80		This is a group voice call
	PVT_VOICE                 = 0x81        This is a private voice call
	GROUP_DATA       		  = 0x83		This is a group data call
	PVT_DATA         		  = 0x84		This is a private data call
	RPT_WAKE_UP               = 0x85        Wakes up all repeaters on the IPSC
	MASTER_REG_REQ     		  = 0x90		Request registration with master (from peer, to master)
	MASTER_REG_REPLY          = 0x91		Master registration request reply (from master, to peer)
	PEER_LIST_REQ    		  = 0x92		Request peer list from master
	PEER_LIST_REPLY 	 	  = 0x93		Master peer list reply
	PEER_REG_REQ              = 0x94		Peer registration request
	PEER_REG_REPLY            = 0x95		Peer registration response
	MASTER_ALIVE_REQ          = 0x96		Master keep alive request (to master)
	MASTER_ALIVE_REPLY        = 0x97		Master keep alive reply (from master)
	PEER_ALIVE_REQ            = 0x98		Peer keep alive request (to peer)
	PEER_ALIVE_REPLY          = 0x99        Peer keep alive reply (from peer)
	DE_REG_REQ                = 0x9a        De-registraiton request (to master or all?)
	DE_REG_REPLY              = 0x9b        De-registration reply (from master or all?)



**AUTHENTICATION:**  
Most IPSC networks will be operated as "authenticated". This means that a key is used to create a digest of the packets exchanged in order to authenticate them. Each node in the IPSC network must have the authentication key programmed in order for the mechanism to work. The process is based on the SHA-1 digest protocol, where the "key" is a 20 byte hexadecimal *string* (if a shorter key is programmed, leading zeros are used to create a 20 byte key). The IPSC payload and the key are used to create the digest, of which only the most significant 10 bytes are used (the last 10 are truncated). This digest is appended to the end of the IPSC payload before transmission. An example is illustrated below:
  
	IPSC Registration Packet		Digest	
	90000000016a000080dc04030400	b0ec45f4c3f8fb0c0b1d
	

**CONNECTION CREATION AND MAINTENANCE:**  
The IPSC network truly "forms" when the first peer registers with the master. All peers register with the master in the same way, with a slight variation from the first peer. Below is a descirption of the process and states in creating a connection, as a peer, and maitaining it.

There are various states, timers and counters associated with each. When peers or the master send us requests, we should answer them immediatley. Our own communcation with them is timed, and may share the same timer. Counter values should be the same for every master and peer in an IPSC. They don't have to be, but that is what mother M does, and it saves a lot of resources.
  
*COMMUNICATION WITH MASTER:*
The following illustrates the communication that a peer (us, for example) has with the master. The peer must register, then send keep-alives at an arbitrary interval (usually 5 - 30 seconds). If more than some arbitrary number of keep-alives are missed, we should return to the beginning and attempt to register again -- but do NOT elimiate the peers list, as peers may still be active. The only additional communcation with the master is if the master sends an unsolicited peer list. In this case, we should update our peer list as appropriate and continue.

									  +-----------------+
									  |Send Registration|
		+---------------------------->|Request To Master|<-------------+
		|                             +--------+--------+              |
		|                                      |                       |
		|                                      v                       |
		|                               +--------------+         +-----+------+
		|                               |Did The Master|   NO    |Wait FW Open|
		|                               |  Respond ?   +-------->|   Timer    |
		|                               +----+-----+---+         +------------+
		|                                    |     |
		|                                    | YES |
		|   +-------------+                  v     |
		|   |Add 1 To Keep|     +----------------+ |             +-------------+
		|   | Alive Missed|     |Send Master Keep| |             |Is Peer Count|
		|   |   Counter   +---->|  Alive Request | +------------>|     > 1 ?   |
		|   +-------------+     +-------+--------+               +------+------+
		|         ^                   |         ^                       | YES
	 YES|         | NO                v         |                       v
	+---+---------+--+      +------------+      |               +-----------------+
	| Is The Missed  |      |Wait FW Open|      |               |Request Peer List|
	|   Keep-Alive   |      |   Timer    |      |               |   From Master   |<-----+
	|Count Exceeded ?|      +-----+------+      |               +-------+---------+      |
	+----------------+                |         |                       |                |
			^                         v         |                       v                |
			|             +--------------+     ++-------------+     +---------+          |
			|        NO   |Did The Master| YES |Set Keep Alive|     |Peer List| NO       |
			+-------------+  Respond ?   +---->| Counter To 0 |     |Received?+----------+
						  +--------------+     +--------------+     +---------+

*COMMUNICATION WITH PEERS:*
Once we have registered with the master, it will send a peer list update to any existing peers. Those peers will **immediately** respond by sending peer registrations to us, and then keep alives once we answer. We should send responses to any such requests as long as we have the peer in our own peer list -- which means we may miss one while waiting for receipt of our own peer list from the master. Even though we receive registration requests and keep-alives from the peers, we should send the same to them, even though this is redundant, it is how we ensure that firewall UDP sessions remain open. A bit wonky, but elegant. For example, a peer may not have a firewall, so it only sends keep-alives every 30 seconds, but we may need to every 5; which we achieve by sending our own keep-alives based on our own timer. The diagram only shows the action for the *initial* peer list reply from the master. Unsolicited peer lists from the master should update the list, and take appropriate action: De-register peers not in the new list, or begin registration for new peers.

								  +-----------------+                              +-------------+
								  |Recieve Peer List|                              |Received Peer|
								  |   From Master   |                              |Leave Notice?|
								  +------+----------+                              +------+------+
										 |                                                |
										 v FOR EACH PEER                                  |
							 +----------------------+                                     v
							 |Send Peer Registration|                                +-----------+
	    +------------------->|       Request        |<-----------+                   |Remove Peer|
	    |                    +----------+-----------+            |                   | From List |
        |                               |                        |                   +-----------+
        |                               v                        |
        |                     +---------------------+     +------+------+
        |     +---------+     |Registration Response| NO  |Wait Firewall|
        |     |+1 Missed|     |     Recieved ?      +---->|  Open Timer |
        |     | Counter |     +---------+-----------+     +-------------+
        |     +-------+-+                   |
        |         ^   |                     v YES
        |         |   |                +----------+
        |         |   +--------------->|Send Peer |
	    |         |          +-------->|Keep Alive|
		|         |          |         +----+-----+
		|YES      |NO        |              |
	+---+---------+--+ +-----+------+       |
	|   Keep Alive   | | Set Missed |       |
	| Count Exceeded?| |Counter to 0|       |
	+----------------+ +------------+       |
               NO ^      ^ YES              |
                  |      |                  v
              +---+------+----+       +-------------+
              |   Peer Keep   |       |Wait Firewall|
              |Alive Received?|<------+  Open Timer |
              +---------------+       +-------------+


**PACKET FORMATS:**  
  
REGISTRATION REQUESTS, KEEP-ALIVE REQUESTS AND RESPONSES:
The fields 'LINKING', 'FLAGS' and 'VERSION' are described in detail in the next section.

	TYPE(1 Byte) + SRC_ID (4 Bytes) + LINKING (1 Byte) + FLAGS (4 Bytes) + VERSION (4 Bytes) [+ AUTHENTICATION (10 Bytes)]
	90 0004C2C0 6A 000080DC 04030400 [AUTHENTICATION (10 Bytes)]

PEER LIST REQUEST:

	TYPE(1 Byte) + SRC_ID (4 Bytes) [+ AUTHENTICATION (10 Bytes)]
	92 0004C2C0 [AUTHENTICATION (10 Bytes)]

PEER LIST RESPONSE:

	TYPE(1 Byte) + SRC_ID (4 Bytes) + PEER_LIST_LENGTH* (2 Bytes) + {PEER_ID, PEER_IP, PEER_PORT, PEER_LINKING}... [+ AUTHENTICATION (10 Bytes)]
	93 0004c2c0 002c 
                 	 	00000001 6ccf7505 c351 6a
                		0004c2c3 d17271e9 c35a 6a
                 	   	0004c2c5 446716bb c35c 6a
                  	  	00c83265 a471c50c c351 6a
                                              		d66a94568d29357205c2
                                                    
    *Number of peers can be derived from PEER_LIST_LENGTH, as each peer entry is 11 bytes (Thanks Hans!)


Number of peers can be derived from PEER_LIST_LENGTH, as each peer entry is 11 bytes

**CAPABILITIES: Bytes 6-14 (6-16 for master reg. reply):**
(Displayed in most to least significant bytes)

***LINKING STATUS: Byte 6***

	Byte 1 - BIT FLAGS:
	      xx.. .... = Peer Operational (01 only known valid value)
	      ..xx .... = Peer MODE: 00 - No Radio, 01 - Analog, 10 - Digital
	      .... xx.. = IPSC Slot 1: 10 on, 01 off 
	      .... ..xx = IPSC Slot 2: 10 on, 01 off

***SERVICE FLAGS: Bytes 7-10 (or 7-12)***

	Byte 1 - 0x00  	= Unknown
	Byte 2 - 0x00	= Unknown
	Byte 3 - BIT FLAGS:
	      x... .... = CSBK Message
	      .x.. .... = Repeater Call Monitoring
	      ..x. .... = 3rd Party "Console" Application
	      ...x xxxx = Unknown - default to 0
	Byte 4 = BIT FLAGS:
	      x... .... = XNL Connected (1=true)
	      .x.. .... = XNL Master Device
	      ..x. .... = XNL Slave Device
	      ...x .... = Set if packets are authenticated
	      .... x... = Set if data calls are supported
	      .... .x.. = Set if voice calls are supported
	      .... ..x. = Unknown - default to 0
	      .... ...x = Set if master
	
	(the following only used in registration response from master)

	NUMBER of PEERS: 2 Bytes
	Byte 5 - 0x00	= Unknown
	Byte 6 - Number of Peers (not including us - ODDLY FORMATTED!!!)

***PROTOCOL VERSION: Bytes 11-14 (or 12-16)***
(These are pure guesses based on repeater and c-Bridge code revisions)

	Bytes 1-2 - 0x04, 0x03 = Current version? (numbering scheme unknown)
	Bytes 3-4 = 0x04, 0x00 = Oldest supported version? (same as above)
  
**SAMPLE CODE:**  
  
*Sample Python3 code to generate the authentication digest:*  

	import binascii
	import hmac
	import hashlib
	
	def add_authentication (_payload, _key):
        _digest = binascii.unhexlify((hmac.new(_key,_payload,hashlib.sha1)).hexdigest()[:20])
        _full_payload = _payload + _digest
        return _full_payload
		
		PAYLOAD = binascii.unhexlify('90000000016a000080dc04030400')            # Registration packet
		KEY = binascii.unhexlify('0000000000000000000000000000000000012345')    # Key '12345'
		
		FULL_PAYLOAD = add_authentication(PAYLOAD, KEY)
		print(binascii.b2a_hex(FULL_PAYLOAD))

**PREFERRED ATTRIBUTION**

Attribution is requested to be given with the following information:

    Title: "DMRlink"
    Source: "http://github.com/n0mjs/DMRlink"

    Author: "K0USY Group"
    Link: "http://www.k0usy.org"

    License: "CC BY-SA 3.0"
    Link: "http://creativecommons.org/licenses/by-sa/3.0/"

An example where Title, Author and License are hyperlinked:
  ["DMRlink"](http://github.com/n0mjs710/DMRlink) by [K0USY Group](http://www.k0usy.org) is licensed under [CC BY-SA 3.0](http://creativecommons.org/licenses/by-sa/3.0/)
    
An example where hyperlinks are not possible:
  "DMRlink" (http://github.com/n0mjs710/DMRlink) by K0USY Group (http://www.k0usy.org) is licensed under CC BY-SA 3.0 (http://creativecommons.org/licenses/by-sa/3.0/)
    
Attribution is requested to be made in any official public or private documentation about the use or derivative use of DMRlink in conjunction with whatever function(s), operation(s) or feature(s) employ DMRlink in whole or in part. Attribution need only be made once per any such "official" documentation and may be placed wherever deemed appropriate by the author of such documentation.

**NOTE:**

This is important: If you e-mail me asking about dmrlink and don't use the phrase "here I am, rock you like a hurricane" (at least initially), I will probably delete your e-mail without reading it. I need to be very clear. This software is NOT intended to be an out-of-box replacement for c-Bridge, SmartPTT, GenWatch, RDAC, etc. Please do not contact me with the express intent of wanting to know how to configure it to do the same thing as any of these fine products in a production environment, because it doesn't do all of the things that they do, and will likely never be something you can "just run" and peform those functions without more knowledge and patience. This is free software, shared with the world so that others can learn from it or do useful things with it. If you want something that is a c-Bridge or SmartPTT, then please go buy one of those products -- they work great, K0USY Group owns and uses both. If you're a tinkerer, or don't need a commercial grade solution, and want to get your "hands dirty", then DMRlink might be right for you. Using dmrlink requires only a very basic understanding of Python. If you have read this README.md, have looked for comments or other direction within the files themsleves, and still can't figure something out, then please e-mail me, and I'll try to help if I can.

***73 DE N0MJS***

Copyright (c) 2013, 2014 Cortney T. Buffington, N0MJS and the K0USY Group. n0mjs@me.com

This work is licensed under the Creative Commons Attribution-ShareAlike
3.0 Unported License.To view a copy of this license, visit
http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
Creative Commons, 444 Castro Street, Suite 900, Mountain View,
California, 94041, USA.
