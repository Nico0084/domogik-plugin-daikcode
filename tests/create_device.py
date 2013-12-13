#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
REST_URL="http://192.168.1.195:40405"
HOST="vmdomogik0"
DEVICE_NAME="Remote_1"
DEVICE_IR = "IRTrans_1"
DEVICE_DATATYPE = "IRTrans standard"
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

def create_device():
    ### create the device, and if ok, get its id in device_id
    print("Creating the device...")
    td = TestDevice()
    print 'host :',  get_sanitized_hostname()
    td.create_device("plugin-daikcode.{0}".format(get_sanitized_hostname()), "test_daikcode.remotearc", "daikcode.remotearc")
    print "Device created"
    td.configure_global_parameters({"device" : DEVICE_NAME, "irdevice": DEVICE_IR, "datatype": DEVICE_DATATYPE})
    print "Device configured" 

if __name__ == "__main__":
    create_device()


# TODO : recup de la config rest
# TODO : passer les parametres a la fonction
# TODO : renommer le fichier pour pouvoir importer la fonction en lib
# TODO : create generic functions for device creation and global parameters
