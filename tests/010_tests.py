#!/usr/bin/python
# -*- coding: utf-8 -*-

from domogik.xpl.common.plugin import XplPlugin
from domogik.xpl.common.xplmessage import XplMessage
from domogik.tests.common.plugintestcase import PluginTestCase
from domogik.tests.common.testplugin import TestPlugin
from domogik.tests.common.testdevice import TestDevice
from domogik.tests.common.testsensor import TestSensor

from testcommand import TestCommand

from domogik.common.utils import get_sanitized_hostname
from datetime import datetime
import unittest
import sys
import os
import traceback
import threading
import time

### global variables
DEVICE_NAME="Remote_1"
DEVICE_IRTRANSMITTER = "IRTrans server"
DEVICE_DATATYPE = "IRTrans standard"
DEVICE_OPTION = "/user/irtrans"

class DaikincodeTestCase(PluginTestCase):

    def test_0100_dummy(self):
        self.assertTrue(True)

    def test_0110_get_switch_state(self):
        """ check if the xpl messages about send xpl_cmnd are OK
            Sample message : 
            xpl-trig
            {
            hop=1
            source=domogik-daikcode.domogik-vm1
            target=*
            }
            daikin.basic
            {
            device= # Name
            command= # a command reference
            key = # command options
            }
        """
        global device_id
        global xpl_plugin
        
        # do the test
        print(u"********** start testing xpl command set_on-off.")
        command = TestCommand(self,  device_id,  'set_on-off')
        print (u'try to send xpl_cmnd fake....')
        self.assertTrue(command.test_XplCmd({"command" : "switch",  "power" : "on"}, {"state" :"on"}))
        msg1_time = datetime.now()
        time.sleep(8)
        print(u"********** start testing xpl command set_temperature.")
        command2 = TestCommand(self,  device_id,  'set_temperature')
        self.assertTrue(command2.test_XplCmd({"command" : "setpoint", "temp": 23, "zone" : "id"}, {"temp" : 23,  "zone": "id"}))
        time.sleep(8)

    def assert_Xpl_Stat_Ack_Wait(self, xplMsg) :
        """Assert a xpltrig for waiting a switch state"""
        print(u"Check that a message about xpl stat ack is sent. The message must be received once time.")
        schema,  data = xplMsg
        print "schema" , schema
        print "data", data
        self.assertTrue(self.wait_for_xpl(xpltype = "xpl-trig",
                                  xplschema = schema,
                                  xplsource = "domogik-{0}.{1}".format(self.name, get_sanitized_hostname()),
                                  data = data,
                                  timeout = 60))
        print "listener ack running"

    def send_xplTrig(self, data):
        """ Send xPL fake message on network
        """
        global xpl_plugin
        
        msg = XplMessage()
        msg.set_type("xpl-trig")
        msg.set_header(source ="domogik-{0}.{1}".format(self.name, get_sanitized_hostname()))
        msg.set_schema("sensor.basic")
        msg.add_data(data)
        print (u"send fake xpl switch on : {0}".format(msg))
        xpl_plugin.myxpl.send(msg)

    def send_xpCmd(self, data):
        """ Send xPL fake message on network
        """
        global xpl_plugin
        
        msg = XplMessage()
        msg.set_type("xpl-cmnd")
     #   msg.set_header(source ="domogik-{0}.{1}".format(self.name, get_sanitized_hostname()))
        msg.set_schema("daikin.basic")
        msg.add_data(data)
        print (u"send fake xpl cmd switch on : {0}".format(msg))
        xpl_plugin.myxpl.send(msg)

if __name__ == "__main__":

    ### configuration

    # set up the xpl features
    xpl_plugin = XplPlugin(name = 'testdaik', 
                           daemonize = False, 
                           parser = None, 
                           nohub = True,
                           test  = True)
    # set test plugin ready for manager
    th = threading.Thread(None, xpl_plugin.ready, "plugin_test_ready") 
    th.start()

    # set up the plugin name
    name = "daikcode"

    # set up the configuration of the plugin
    # configuration is done in test_0010_configure_the_plugin with the cfg content
    # notice that the old configuration is deleted before
    cfg = {'configured' : True }

    ### start tests

    # load the test devices class
    td = TestDevice()

    # delete existing devices for this plugin on this host
    client_id = "{0}-{1}.{2}".format("plugin", name, get_sanitized_hostname())
    try:
        td.del_devices_by_client(client_id)
    except:
        print(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
        sys.exit(1)

    # create a test device
    try:
        device_id = td.create_device(client_id, "test_daikcode_remotearc", "daikcode.remotearc")
        params = {"device" : DEVICE_NAME, "irtransmitter" : DEVICE_IRTRANSMITTER, "datatype": DEVICE_DATATYPE, "options": DEVICE_OPTION}
        print (u"configure_global_parameters : {0}".format(params))
        td.configure_global_parameters({"device" : DEVICE_NAME, "irtransmitter" : DEVICE_IRTRANSMITTER, "datatype": DEVICE_DATATYPE, "options": DEVICE_OPTION})
    except:
        print(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        sys.exit(1)

    ### prepare and run the test suite
    suite = unittest.TestSuite()
    # check domogik is running, configure the plugin
    suite.addTest(DaikincodeTestCase("test_0001_domogik_is_running", xpl_plugin, name, cfg))
    suite.addTest(DaikincodeTestCase("test_0010_configure_the_plugin", xpl_plugin, name, cfg))

    # start the plugin
    suite.addTest(DaikincodeTestCase("test_0050_start_the_plugin", xpl_plugin, name, cfg))

    # do the specific plugin tests
    suite.addTest(DaikincodeTestCase("test_0110_get_switch_state", xpl_plugin, name, cfg))

   # do some tests comon to all the plugins
    suite.addTest(DaikincodeTestCase("test_9900_hbeat", xpl_plugin, name, cfg))
    suite.addTest(DaikincodeTestCase("test_9990_stop_the_plugin", xpl_plugin, name, cfg))
    unittest.TextTestRunner().run(suite)

    # quit
    xpl_plugin.force_leave()