# bluecatmigrator

Script to extract all IPAM data from Bluecat Address Manager.  This script will export IPAM data as 3 separate .csv files formatted specifically for Netbox, but can easily be tweaked depending on your needs.

## Prerequisites

You will need python3 installed and a user created on your BAM server with API access.

### Export the data

once this repo is cloned all you need to do is run:

```
python exportall.py
```

Enter your username/password and the FQDN of the server.  Example:

```
PS C:\Users\myuser\Documents\projects\2019\netbox\bluecat> python .\exportall.py
API Username: apiuser
API password:
Bluecat Server FQDN: server.domain.name
```

### Formatting

Netbox requires a vrf before we can start assigning the IPs to interfaces, and as most of my IPs are not in a vrf, I gave them all a default "1" vrf - IPs actually in a vrf will be updated after the fact.

ENJOY!

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
