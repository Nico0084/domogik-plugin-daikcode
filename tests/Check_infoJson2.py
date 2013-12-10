#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
REST_URL="http://192.168.1.195:40405"
HOST="vmdomogik0"
DEVICE_NAME="Daikin remote 1"
# path in the filesystem for the device 
DEVICE_ADDRESS="/home"      
# interval in minutes between each poll
DEVICE_INTERVAL=1
########################################################


import json
import sys
from domogik.common.packagejson import PackageJson

#json_file = "d:\Python_prog\domogik-plugin-daikcode\info.json"
json_file = "/home/admdomo/Partage-VM/domogik-plugin-daikcode/info.json"

data = json.load(open(json_file))
print data
print 'Domogik validation ...'
p = PackageJson(path=json_file)
p.validate()
print 'Fin validation fichier {0}'.format(json_file)
