##DMRlink FAQ
**PURPOSE:** Since DMRlink was published, a number of similar questions have come in regarding it's use. This FAQ will attempt to address common questions or concerns.

**Can DMRlink bridge networks like a c-Bridge?** Yes, it can bridge IPSC networks, but no, not not quite like a c-Bridge. DMRlink is able to bridge IPSC networks, it is able to selectively "choose" which TGIDs to bridge and which not to bridge, and it can re-write the TGID, but it cannot change the timeslot of a transmission. If it comes in on TS1, it will have to go back out on TS1. It also does not have automatic scheduling or "trigggering" of bridge events.

**Someone said DMRlink "bricked" their repeater, is it safe to use?** DMRlink has no abilty to speak the XNL/XCMP protocol (which involves encrypted keys) that Motorla uses to control radios and repeaters. DMRlink simply cannot even remotely speak the language necessary to do this.

**DMRlink is OpenSource, but IPSC is proprietary, will I get in trouble for using it?** DMRlink is an original interpretation of the IPSC protocol. It's probably not quite 100% correct, and it certainly doesn't implement every last feature in IPSC. It is not being sold, and it is not presented as a replacement for exising commercial software. We have received no complaints from Motorola regarding this project. We do not believe using it will be a problem -- if there's a problem, it will be with those of us who wrote it, and to date, we have recieved no complaints.

**Was DMRlink created by hacking the c-Bridge and/or SmartPTT?** Absolutely not! DMRlink was created using wireshark to capture packets between IPSC speaking endpoints on an IPSC network and pattern-matching. For example, when we know the transmisison was from radio ID 12345, we assume that when we find 12345 in the data stream, that's the source radio ID... we then further match patterns to validate what we find. This is why DMRlink will likely never include all features in IPSC, like XNL/XCMP for example, which uses encryption that makes pattern matching virutally impossible.

**Will you help me get it working?** DMRlink is not commercial software, and nobody is getting paid to write it. The work here represnets HUNDREDS of hours of volunteer effort. We will help as we can, but you must be familiar with IP data networking, very basic programming (preferably python) and IPSC or you will likely have a very hard time getting it to work to your satisfaction.
 

***73 DE N0MJS***
