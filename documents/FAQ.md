##DMRlink FAQ
**PURPOSE:** Since DMRlink was published, a number of similar questions have come in regarding it's use. This FAQ will attempt to address common questions or concerns.

**Can DMRlink bridge networks like a c-Bridge?** Yes, bridge.py can bridge IPSC networks, but no, not not quite like a c-Bridge. It does not have automatic scheduling or "trigggering" of bridge events. Currently bridge rules must all be static.

**Someone said DMRlink "bricked" their repeater, is it safe to use?** DMRlink has no abilty to speak the XNL/XCMP protocol (which involves encrypted keys) that Motorla uses to control radios and repeaters. DMRlink simply cannot even remotely speak the language necessary to do this.

**DMRlink is OpenSource, but IPSC is proprietary, will I get in trouble for using it?** DMRlink is an original interpretation of the IPSC protocol. It's probably not quite 100% correct, and it certainly doesn't implement every last feature in IPSC. It is not being sold, and it is not presented as a replacement for exising commercial software. We have received no complaints from Motorola regarding this project. We do not believe using it will be a problem -- if there's a problem, it will be with those of us who wrote it, and to date, we have recieved no complaints.

**Was DMRlink created by hacking the c-Bridge and/or SmartPTT?** Absolutely not! DMRlink was created using wireshark to capture packets between IPSC speaking endpoints on an IPSC network and pattern-matching. For example, when we know the transmisison was from radio ID 12345, we assume that when we find 12345 in the data stream, that's the source radio ID... we then further match patterns to validate what we find. This is why DMRlink will likely never include all features in IPSC, like XNL/XCMP for example, which uses encryption that makes pattern matching virutally impossible.

**Why can't DMRlink talk to my c-Bridge over a CC-CC connection??** The c-Bridge CC-CC connection is a proprietary system written by Ravennet Systems. It is not part of IPSC, and is used only between c-Bridge, TL-NET and other Ravennet-based RoIP systems. The DMRlink project only deals with IPSC. As such it doesn't communicate with SmartPTT radioserver-to-radioserver links either.

**Will you help me get it working?** DMRlink is not commercial software, and nobody is getting paid to write it. The work here represents HUNDREDS of hours of volunteer effort. We will help as we can, but you must be familiar with IP data networking, very basic programming (preferably python) and IPSC or you will likely have a very hard time getting it to work to your satisfaction.
 

***73 DE N0MJS***
