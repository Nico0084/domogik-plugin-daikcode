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
# A debugging code checking import error
try:
    from domogik.common.plugin import Plugin
    import zmq
    import threading
    from domogikmq.message import MQMessage
    from domogikmq.reqrep.client import MQSyncReq

    from domogik_packages.plugin_daikcode.lib.daikcode import RemoteManager, getRemoteId
    import traceback
except ImportError as exc :
    import logging
    logging.basicConfig(filename='/var/log/domogik/daikcode_start_error.log', level=logging.DEBUG)
    log = logging.getLogger('daikcode_start_error')
    err = "Error: Plugin Starting failed to import module ({})".format(exc)
    print err
    logging.error(err)
    print log

class DaikinManager(Plugin):
    """ Envois et recois des codes xPL IR DAIKIN
    """

    def __init__(self):
        """ Init plugin
        """
        Plugin.__init__(self, name='daikcode')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return

        # get the devices list
        self.devices = self.get_device_list(quit_if_no_device = False)
        # get the config values
        self.remoteManager = RemoteManager(self, self.send_sensor, self.send_cmd)
        for a_device in self.devices :
            try :
                if a_device['device_type_id'] != 'daikcode.remotearc' :
                #if device_name == None  or irtransmitter == None or options == None :
                    self.log.error(u"No daikcode.remotearc device type")
                    break
                else :
                    self.remoteManager.addRemote(a_device)
                    self.log.debug("Ready to work with device {0}".format(getRemoteId(a_device)))
            except:
                self.log.error(traceback.format_exc())
                # we don't quit plugin if an error occured
                #self.force_leave()
                #return
         # Register pub client sensor
        self.add_mq_sub('client.sensor')
        print "Plugin ready :)"
        self.log.info("Plugin ready :)")
        self.ready()

    def on_message(self, msgid, content):
        #Transmit mq message to manager
        Plugin.on_message(self, msgid, content)
        if msgid == 'client.sensor':
            self.remoteManager.handle_sensor_pub(content)

    def on_mdp_request(self, msg):
        # display the req message
        Plugin.on_mdp_request(self, msg)
        # call a function to reply to the message depending on the header
        action = msg.get_action()
        if action == "client.cmd" :
            self.log.debug("cmds listener received message:{0}".format(msg))
            find, status, reason, callback =  self.remoteManager.handle_cmd_request(msg.get_data())
            print(find, status, reason, callback)
            if find :
                reply_msg = MQMessage()
                reply_msg.set_action('client.cmd.result')
                reply_msg.add_data('status', status)
                reply_msg.add_data('reason', reason)
                self.reply(reply_msg.get())
                print(u"**** reply sended")
                if callback is not None :
                    print(u"**** call callback ...")
                    threading.Thread(None, callback(), "th_callback-{0}".format(action), (), {}).start()

    def send_cmd(self, client, device_id, command_id, params):
        """ Send cmd message over MQ"""
        cli = MQSyncReq(zmq.Context())
        msg = MQMessage()
        msg.set_action('cmd.send')
        msg.add_data('device_id', device_id)
        msg.add_data('command_id', command_id)
        for param in params :
            msg.add_data(param, params[param])
        self.log.info(u"Sending MQ message to {0} for device {1}, command {2} with params:{3}" .format(client, device_id, command_id, params))
        print cli.request(str(client), msg.get(), timeout=10)

    def send_sensor(self, device, sensor_id, dt_type, value):
        """Send pub message over MQ"""
        dt_Type = self.get_data_type(dt_type)
        if dt_Type :
            if 'labels' in dt_Type :
                for k, v in dt_Type['labels'].iteritems():
                    if value == k or value == v :
                        value = k
                        break;
            elif 'values' in dt_Type :
                for k, v in dt_Type['values'].iteritems():
                    if value == k or value == v :
                        value = k
                        break;
        self.log.info(u"Sending MQ sensor id:{0}, dt type: {1}, value:{2}" .format(sensor_id, dt_type, value))
        self._pub.send_event('client.sensor',
                         {sensor_id : value})


    def handle_xpl_trig(self, message):
        """ Process xpl schema ir.basic
        """
        self.log.debug("xpl-trig listener received message:{0}".format(message))
        device_name = message.data['device']
        self.log.debug("device :" + device_name)
        idsRemote = self.remoteManager.getIdsRemote(device_name)
        find = False
        if idsRemote != [] :
            for id in idsRemote :
                remote = self.remoteManager.getRemote(id)
                if remote :
                    self.log.debug("Handle xpl-trig for remote :{0}".format(message.data['device']))
                    find = True
                    remote.handle_xpl_trig(message.data)
        if not find : self.log.debug("xpl-trig received for unknowns remote :{0}".format(message.data['device']))



if __name__ == "__main__":
    DaikinManager()

