# To provide more readable output from DMRlink with current subscriber and repeater IDs, we download the CSV files from DMR-MARC
# If you are going to use this in a cron task,  don't run it more then once a day.
# It might be good to find alternale a source as a backup.

# <http://www.dmr-marc.net/cgi-bin/trbo-database/datadump.cgi>

# wget -O users.csv -q "http://www.dmr-marc.net/cgi-bin/trbo-database/datadump.cgi?table=users&format=csv&header=0"

# Options are:

# table { users | repeaters }

# format { table | csv | csvq | json }

# header { 0 | 1 } (only applies to table and csv formats)

# id { nnnnnn } (query an individual record)

# Get the user IDs.
wget -O subscriber_ids.csv -q "http://www.dmr-marc.net/cgi-bin/trbo-database/datadump.cgi?table=users&format=csv&header=0"

# Get the peer IDs
wget -O peer_ids.csv -q "http://www.dmr-marc.net/cgi-bin/trbo-database/datadump.cgi?table=repeaters&format=csv&header=0"

