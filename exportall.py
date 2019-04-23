"""
-
Bluecat IP Exporter
--
run with:
python exportall.py
---
This script will export the following from the Bluecat Management Server:
* IP Prefixes ("supernets")
* Subnets
* IP addresses
-----
Expected runtime (From the LAN for 50k addresses, 1k Networks): ~.5 hours
Expected Output:
    IP4Blocks.csv
    IP4Networks.csv
    IP4addresses.csv
!!! Currently limited to 10 Million objects per query (Block/Network/Addr are separate queries)
Update script if you have more than that...
"""
import requests, json, getpass, sys, urllib3, csv, re, fileinput, os, getpass, sys, ipaddress
import datetime as dt

networklist = []
user = input("API Username: ")
password = getpass.getpass(prompt='API password: ')
"""
Get the hostname of the Bluecat server we are interrogating
"""
bamurl = input("Bluecat Server FQDN: ")

"""
reusable function to get addresses by type
"""

def bmcustresponse(keyword,type):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    mainurl = "https://"+bamurl+"/Services/REST/v1/"
    loginurl = mainurl+"login?"
    logouturl = mainurl+"logout?"
    param = {"username":user,"password":password}
    response = requests.get(loginurl, params=param, verify=False)
    token = str(response.json())
    token = token.split()[2]+" "+token.split()[3]
    header={'Authorization':token,'Content-Type':'application/json'}
    now = dt.datetime.now()
    headertime = now.strftime('%H-%M')
    searchURL = mainurl+"searchByObjectTypes?"
    searchParams = {
    "keyword":keyword,
    "types":type,
    "start":"0",
    "count":"10000000"
    }
    custresponse = requests.get(searchURL,params=searchParams,headers=header,verify=False)
    response=requests.get(logouturl,headers=header,verify=False)
    return custresponse

"""
reusable function to massage data for import into netbox
"""

def csvcreator(jsondata,type,networklist):
    write_data = open(type + ".csv", 'w', encoding='utf-8-sig')
    csvwriter = csv.writer(write_data)
    count = 0
    for data in jsondata:
        if count == 0:
            jsonheader = data.keys()
            csvwriter.writerow(jsonheader)
            count +=1
        if data != None:
            csvwriter.writerow(data.values())
    write_data.close()
    # Now massage data depending on type
    if type == "IP4Block":
        with open(type + ".csv", "r") as f:
            with open (type + ".csv.new", "w") as f1:
                for line in f:
                    pattern1 = re.compile("id\,name\,type\,properties")
                    pattern2 = re.compile("(^\d+,)(.*?)(IP4.*?\,CIDR=)(.*?)(\|.*locationInherited=.*?\|)(.*?\|)$")
                    result1 = pattern1.search(line)
                    result2 = pattern2.search(line)
                    if result1:
                        f1.write("description,prefix,vrf,status,tenant\n")
                    if result2:
                        if result2.group(2) != ",":
                            f1.write(str(result2.group(2)) + str(result2.group(4)) + ",1,Active,Multnomah County\n")
                        else:
                            #No name defined for prefix, mark as Deprecated (update after...)
                            f1.write(str(result2.group(2)) + str(result2.group(4)) + ",1,Deprecated,Multnomah County\n")
        os.remove(type + ".csv")
        os.rename(type + ".csv.new",type + ".csv")
    if type == "IP4Network":
        with open(type + ".csv", "r") as f:
            with open (type + ".csv.new", "w") as f1:
                for line in f:
                    pattern1 = re.compile("id\,name\,type\,properties")
                    pattern2 = re.compile("(^\d+,)(.*?)(IP4.*?\,)CIDR=(.*?)(\|.*inheritPingBeforeAssign=.*?\|)(gateway=.*?)(\|.*?inheritDNSRestrictions=.*?\|)$")
                    result1 = pattern1.search(line)
                    result2 = pattern2.search(line)
                    if result1:
                        f1.write("description,address,vrf,status,tenant\n")
                    if result2:
                        if result2.group(2) != ",":
                            f1.write(str(result2.group(2)) + str(result2.group(4)) + ",1,Active,Multnomah County\n")
                        else:
                            #No name defined for prefix, mark as Deprecated
                            f1.write(str(result2.group(2)) + str(result2.group(4)) + ",1,Deprecated,Multnomah County\n")
        os.remove(type + ".csv")
        os.rename(type + ".csv.new",type + ".csv")
    if type == "IP4Address":
        with open(type + ".csv", "r", encoding='utf-8-sig') as f:
            with open (type + ".csv.new", "w", encoding='utf-8-sig') as f1:
                for line in f:
                    pattern1 = re.compile("id\,name\,type\,properties")
                    pattern2 = re.compile("(^\d+),(.*?\,)(IP4Address\,).*address=(\d+\.\d+\.\d+\.\d+)\|state=(\w+)")
                    pattern3 = re.compile("CIDR=.*\/(\d+)")
                    pattern4 = re.compile("\d+\.\d+\.\d+\.\d+\/(\d+)")
                    result1 = pattern1.search(line)
                    result2 = pattern2.search(line)
                    if result1:
                        f1.write("description,address,vrf,status\n")
                    if result2:
                        if "DHCP" in str(result2.group(5)):
                            for network in networklist:
                                if ipaddress.IPv4Address(result2.group(4)) in ipaddress.IPv4Network(network):
                                    mask = pattern4.search(network)
                                    break
                            f1.write("," + str(result2.group(4)) + "/" + str(mask.group(1)) + ",1,DHCP\n")
                        else:
                            for network in networklist:
                                if ipaddress.IPv4Address(result2.group(4)) in ipaddress.IPv4Network(network):
                                    mask = pattern4.search(network)
                                    break
                            if result2.group(2) == ",":
                                if result2.group(5) == "GATEWAY":
                                    #reserve gateways by default, even if unnamed...
                                    f1.write(str(result2.group(4)) + "_GATEWAY," + str(result2.group(4)) + "/" + str(mask.group(1)) + ",1,Active\n")
                            if "RESERVED" in str(result2.group(5)):
                                f1.write(str(result2.group(2)) + str(result2.group(4)) + "/" + str(mask.group(1)) + ",1,Active\n")
                            if "STATIC" in str(result2.group(5)):
                                f1.write(str(result2.group(2)) + str(result2.group(4)) + "/" + str(mask.group(1)) + ",1,Active\n")
        os.remove(type + ".csv")
        os.rename(type + ".csv.new",type + ".csv")


"""
Start By getting an export of ALL Prefixes and placing them in a list as well as
an importable CSV to be used by Netbox
"""

allprefixes = bmcustresponse("*","IP4Block")
allprefixes = allprefixes.json()
csvcreator(allprefixes,"IP4Block",networklist)

"""
Get all networks then export them as a list to use locally so we don't need to make a
recursive call to look up every mask
"""
allnetworks = bmcustresponse("*","IP4Network")
allnetworks = allnetworks.json()
# Convert networks to list to parse locally
for data in allnetworks:
    tosearch = data['properties']
    netpattern = re.compile("CIDR=(\d+\.\d+\.\d+\.\d+\/\d+)|")
    netmatch = netpattern.search(tosearch)
    if netmatch.group(1):
        networklist.append(netmatch.group(1))
csvcreator(allnetworks,"IP4Network",networklist)

"""
Get all IP addresses reserved - this may take several minutes
"""

allipaddrs = bmcustresponse("*","IP4Address")
allipaddrs = allipaddrs.json()
csvcreator(allipaddrs,"IP4Address",networklist)

"""
Optional: Export all IP addresses as JSON file to be consumed by other sources.
NOTE: exporting all with * resulted in several 'Nonetype' entires.
"""
#with open('allipaddrs.json', 'w') as outfile:
#    json.dump(allipaddrs, outfile)
