#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

generate control code for the IR protocol DAIKIN air conditioners

Implements
==========

- DiskManager

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2007-2013 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.xpl.common.xplmessage import XplMessage
from domogik.xpl.common.plugin import XplPlugin
from domogik.xpl.common.queryconfig import Query
from domogik.mq.reqrep.client import MQSyncReq
from domogik.mq.message import MQMessage

from packages.plugin_daikcode.lib.daikincode import CodeIRDaikin
import threading
import traceback


class DaikinManager(XplPlugin):
    """ Envois et recois des code xPL ir DAIKIN
    """

    def __init__(self):
        """ Init plugin
        """
        XplPlugin.__init__(self, name='daikcode')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return

        # get the devices list
        self.devices = self.get_device_list(quit_if_no_device = True)
       

        disk_manager = Disk(self.log, self.send_xpl, self.get_stop())

        ### Start listening each path
        threads = {}
        for a_device in self.devices:
            try:
                # feature get_total_space
                path = self.get_parameter_for_feature(a_device, "xpl_stats", "get_total_space", "device")
                interval = self.get_parameter_for_feature(a_device, "xpl_stats", "get_total_space", "interval")
                self.log.info("Start monitoring totel space for '%s'" % path)
                thr_name = "{0}-{1}".format(a_device['name'], "get_total_space")
                threads[thr_name] = threading.Thread(None,
                                               disk_manager.get_total_space,
                                              thr_name,
                                              (path, interval,),
                                              {})
                threads[thr_name].start()

                # feature get_free_space
                path = self.get_parameter_for_feature(a_device, "xpl_stats", "get_free_space", "device")
                interval = self.get_parameter_for_feature(a_device, "xpl_stats", "get_free_space", "interval")
                self.log.info("Start monitoring free space for '%s'" % path)
                thr_name = "{0}-{1}".format(a_device['name'], "get_free_space")
                threads[thr_name] = threading.Thread(None,
                                               disk_manager.get_free_space,
                                              thr_name,
                                              (path, interval,),
                                              {})
                threads[thr_name].start()

                # feature get_used_space
                path = self.get_parameter_for_feature(a_device, "xpl_stats", "get_used_space", "device")
                interval = self.get_parameter_for_feature(a_device, "xpl_stats", "get_used_space", "interval")
                self.log.info("Start monitoring used space for '%s'" % path)
                thr_name = "{0}-{1}".format(a_device['name'], "get_used_space")
                threads[thr_name] = threading.Thread(None,
                                               disk_manager.get_used_space,
                                              thr_name,
                                              (path, interval,),
                                              {})
                threads[thr_name].start()

                # feature get_percent_used
                path = self.get_parameter_for_feature(a_device, "xpl_stats", "get_percent_used", "device")
                interval = self.get_parameter_for_feature(a_device, "xpl_stats", "get_percent_used", "interval")
                self.log.info("Start monitoring percent used for '%s'" % path)
                thr_name = "{0}-{1}".format(a_device['name'], "get_percent_used")
                threads[thr_name] = threading.Thread(None,
                                               disk_manager.get_percent_used,
                                              thr_name,
                                              (path, interval,),
                                              {})
                threads[thr_name].start()

            except:
                self.log.error(traceback.format_exc())
                # we don't quit plugin if an error occured
                # a disk can have been unmounted for a while
                #self.force_leave()
                #return



        self.ready()
        self.log.info("Plugin ready :)")


    def send_xpl(self, path, du_type, du_value):
        """ Send xPL message on network
        """
        self.log.debug("Values for {0} on {1} : {2}".format(du_type, path, du_value))
        msg = XplMessage()
        msg.set_type("xpl-stat")
        msg.set_schema("sensor.basic")
        msg.add_data({"device" : path})
        msg.add_data({"type" : du_type})
        msg.add_data({"current" : du_value})
        self.myxpl.send(msg)


if __name__ == "__main__":
    DaikinManager()

