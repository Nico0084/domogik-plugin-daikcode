#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
DEVICE_NAME="Remote_1"
DEVICE_IR = "IRTrans_ws"
DEVICE_DATATYPE = "BinTimings"
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

plugin =  "daikcode"

def create_device():
    ### create the device, and if ok, get its id in device_id
    client_id  = "plugin-{0}.{1}".format(plugin, get_sanitized_hostname())
    print("Creating the Remote device...")
    td = TestDevice()
    params = td.get_params(client_id, "daikcode.remotearc")
        # fill in the params
    params["device_type"] = "daikcode.remotearc"
    params["name"] = "test_daikcode.remotearc"
    params["reference"] = "ARC Remote"
    params["description"] = "Connected to {0}".format(DEVICE_IR)
    for idx, val in enumerate(params['no-xpl']):
        if params['no-xpl'][idx]['key'] == 'irdevice' :  params['no-xpl'][idx]['value'] = DEVICE_IR
        if params['no-xpl'][idx]['key'] == 'datatype' :  params['no-xpl'][idx]['value'] = DEVICE_DATATYPE

    for idx, val in enumerate(params['xpl']):
        params['xpl'][idx]['value'] = DEVICE_NAME

    # go and create
    td.create_device(params)
    print "Device Remote {0} configured".format(DEVICE_NAME) 
    

if __name__ == "__main__":
    create_device()

