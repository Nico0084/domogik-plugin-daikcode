# !/usr/bin/python
#-*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}$

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

Generate control code for the IR protocol DAIKIN air conditioners

Implements
==========

- Daikin code IR

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2007-2013 Domogik project
@license: GPL(v3)
@organization: Domogik
"""
import threading
import zmq
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage
from domogik.common.utils import get_sanitized_hostname
from domogik_packages.plugin_daikcode.lib.daikin_encode import CodeIRDaikin

def getRemoteId(device):
    """Return key remote id."""
    if device.has_key('name') and device.has_key('id'):
        return "{0}_{1}".format(device['name'], + device['id'])
    else : return None

class DaikinManagerException(Exception):
    """"Daikcode Manager exception  class"""

    def __init__(self, value):
        self.msg = "Daikcode manager exception : " + value
        Exception.__init__(self, self.msg)


class RemoteManager():
    """Manager for all remotes"""

    def __init__(self, plugin, cb_send_sensor, cb_send_cmd):
        """ Init manager remote objet
            @param plugin  : plugin instance
            @param cb_send_sensor : callback to send msg
            @param cb_send_cmd : callback to send cmd to IRtranceiver
        """
        self._Plugin = plugin
        self._cb_send_sensor = cb_send_sensor
        self._cb_send_cmd = cb_send_cmd
        self._stop = plugin.get_stop()  # TODO : pas forcement util ?
        self.remotes = {} # list of daikin remote control object
        self._Plugin.log.info(u"Remote Manager is ready.")

    def addRemote(self, device):
        """Add a remote from domogik device"""
        name = getRemoteId(device)
        if self.remotes.has_key(name) :
            self._Plugin.log.debug(u"Remote Manager : remote {0} already exist, not added.".format(name))
            return False
        else:
            self.remotes[name] = DaikinRemote(self, device, self._Plugin.log)
            self._Plugin.log.info(u"Remote Manager : created new remote {0}.".format(name))
#            print "Add remote :"
#            pprint.pprint(device)
            return True

    def removeRemote(self, name):
        """Remove a remote and close it"""
        remote = self.getRemote(name)
        if remote :
            remote.close()
            self.remotes.pop(name)

    def getRemote(self, id):
        """Get remote object by id."""
        if self.remotes.has_key(id) :
            return self.remotes[id]
        else :
            return None

    def getIdsRemote(self, idToCheck):
        """Get remote key ids."""
        retval =[]
        findId = ""
#        self._Plugin.log.debug (u"getIdsRemote check for device : {0}".format(idToCheck))
        if isinstance(idToCheck,  DaikinRemote) :
            for id in self.remotes.keys() :
                if self.remotes[id] == idToCheck :
                    retval = [id]
                    break
        else :
            if isinstance(idToCheck,  str) :
                findId = idToCheck
            else :
                if isinstance(idToCheck,  dict) :
                    if idToCheck.has_key('device') : findId = idToCheck['device']
                    else :
                        if idToCheck.has_key('name') and idToCheck.has_key('id'):
                            findId = getRemoteId(idToCheck)
            if self.remotes.has_key(findId) :
                retval = [findId]
            else :
                for id in self.remotes.keys() :
                    if self.remotes[id].getDomogikDevice == findId :
                        retval.append(id)
                    elif self.remotes[id].getIRDevice == idToCheck :
                        retval.append(id)
        self._Plugin.log.debug(u"getIdsRemote for '{0}' return : {1}".format(idToCheck, retval))
        return retval

    def refreshRemoteDevice(self,  remote):
        """Request a refresh domogik device data for a remote."""
        cli = MQSyncReq(zmq.Context())
        msg = MQMessage()
        msg.set_action('device.get')
        msg.add_data('type', 'plugin')
        msg.add_data('name', self._Plugin.get_plugin_name())
        msg.add_data('host', get_sanitized_hostname())
        result = cli.request('dbmgr', msg.get(), timeout=10)
        if result :
            devices = result.get_data()['devices']
            for a_device in devices:
                if a_device['device_type_id'] == remote._device['device_type_id']  and a_device['id'] == remote._device['id'] :
                    if a_device['name'] != remote.device['name'] : # rename and change key remote id
                        old_id = getRemoteId(remote._device)
                        self.remotes[getRemoteId(a_device)] = self.remotes.pop(old_id)
                        self._Plugin.log.info(u"Remote {0} is rename {1}".format(old_id,  getRemoteId(a_device)))
                    remote.updateDevice(a_device)
                    break

    def handle_sensor_pub(self, message):
        """Handle a sensor message from MQ"""
        for id in self.remotes.keys() :
            for sensor_id in message :
                sensor = self.remotes[id].get_sensor_link(sensor_id)
                if sensor :
                    self._Plugin.log.debug(u"MQ Pub message receive {0} for sensor {1}".format(message, sensor['name']))
                    self.remotes[id].handle_sensor_pub(sensor, message[sensor_id])
                    break

    def handle_cmd_request(self, message):
        """Handle a client.cmd message from MQ"""
        for id in self.remotes.keys() :
            print(u"Search in id {0} command id : {1}".format(id, message['command_id']))
            cmd = self.remotes[id].get_command(message['command_id'])
#            print(u"cmd remote {0}".format(cmd))
            if cmd :
                return self.remotes[id].handle_cmd_request(cmd, message)
        return False, False, "", None

    def sendMQAck(self, device, sensor, value):
        """Send an ack xpl message"""
        self._Plugin.log.debug(u"Send ack {0}, {1}".format(value, sensor))
        self._manager._cb_send_sensor(device, sensor['id'], sensor['data_type'], value)

class DaikinRemote():
    """Remote control type Daikin object"""

    def __init__(self, manager, device, log):
        """Init remote control type daikin"""
        self._manager = manager
        self._device = None
        self._dmgDeviceLink = None
        self._log = log
        self.updateDevice(device)
        self.cmdCode = CodeIRDaikin(self,  self._device['name'])
        if self._dmgDeviceLink is not None :
            self.udpateAllFromCode(self._dmgDeviceLink['sensors']['code_ir']['last_value'], True)
        self._currentAck = []

    # On accède aux attributs uniquement depuis les property
    getRemoteId = property(lambda self: getRemoteId(self._device))
    getDomogikDevice = property(lambda self: self._getDomogikDevice())
    getIRDevice = property(lambda self: self._getIRDevice())

    def updateDevice(self, device):
        """Update device data."""
        self._device = device
        cli = MQSyncReq(zmq.Context())
        msg = MQMessage()
        msg.set_action('device.get')
        self._dmgDeviceLink = None
        result = cli.request('dbmgr', msg.get(), timeout=10)
        iRdevice = self._getIRDevice()
        if result and iRdevice :
            devices = result.get_data()['devices']
            for a_device in devices:
                if a_device['id'] == iRdevice :
                    self._dmgDeviceLink = a_device
                    break
            self._log.info(u"Remote {0} linked with device {1}, cmd : {2}, sensor{3}".format(self.getRemoteId, iRdevice, self._dmgDeviceLink['commands'], self._dmgDeviceLink['sensors']))
        else :
            self._log.info(u"Remote {0} no link find with device transmiter, check device parameter <IRDmgDevice>".format(self.getRemoteId))

    def get_sensor_link(self, sensor_id):
        """Check if sensor id correspond to remote"""
        sensor_id = int(sensor_id)
        if self._dmgDeviceLink is not None :
            for sensor in self._dmgDeviceLink['sensors'].values() :
                if sensor['id'] == sensor_id :
                    return sensor
        return False

    def get_command_link(self, command_id):
        """Check if command id correspond to device link"""
        command_id = int(command_id)
        if self._dmgDeviceLink is not None :
            for cmd in self._dmgDeviceLink['commands'].values() :
                if cmd['id'] == command_id :
                    return cmd
        return False

    def get_command(self, command_id):
        """Check if command id correspond to remote"""
        command_id = int(command_id)
        if self._device is not None :
            for cmd in self._device['commands'].values() :
                if cmd['id'] == command_id :
                    return cmd
        return False

    def _getDomogikDevice(self):
        """Return device Id for xPL domogik device"""
        if self._device :
            if 'IRDmgdevice' in self._device['parameters']:
                return int(self._device['parameters']['IRDmgDevice']['value'])
        return None

    def _getDatatype(self):
        """Return datatype for xPL domogik device
            "1" : "BinTimings",
            "2" : "IR Raw",
            "3" : "IR Hexa"
        """
        if self._device :
            type = 'Unknown'
            if self._device['parameters']["datatype"]['value'] == "1" :
                type = "bintimings"
            elif self._device['parameters']["datatype"]['value'] == "2" :
                type = "raw"
            elif self._device['parameters']["datatype"]['value'] == "3" :
                type =  "hexa"
            return type
        else : return None

    def _getIRDevice(self):
        """Return IRDevice for IRTrans."""
        if self._device : return self._manager._Plugin.get_parameter(self._device, 'IRDmgDevice')
        else : return ""

    def sendToIRdevice(self):
        """Send xpl-cmnd to IRTrans Transmitter."""
        # TODO : Handle all IR Datatype
        dataType =  self._getDatatype()
        data = {}
        if dataType == "bintimings" :
            data["code"] = self.cmdCode.encodeCmdIRTrans()
            data["timing"] = self.cmdCode.timing.encodeTimingIRTrans()
        elif dataType == "raw" :
            data["code"] = self.cmdCode.encodeCmdIRTrans()
        elif dataType == "hexa" :
            data["code"] = self.cmdCode.encodeCmdIRTrans()
        for irCmd in self._dmgDeviceLink['commands'] :
            if irCmd.find(dataType) != -1 :
                print(u"Send IR cmd type {0}".format(irCmd))
                client = self._dmgDeviceLink['client_id']
                self._manager._cb_send_cmd(client, self._dmgDeviceLink['id'], self._dmgDeviceLink['commands'][irCmd]['id'] , data)
                break
        else : self._log.info (u"datatype : {0} not handled, cmnd to IR transmitter not send.".format(dataType))

    def sendSensorUpdate(self, item):
        """Send sensor to domogik device."""
        for cmd in item :
            for sensor in self._device['sensors'].values ():
                if sensor["reference"] == cmd:
                    if cmd in ['datetime', 'starttime',  'stoptime'] :
                        value = self.cmdCode.formatStrDelais(item[cmd])
                    else :
                        value = item[cmd]
                    self._manager._cb_send_sensor(self._device, sensor['id'], sensor['data_type'], value)

    def udpateAllFromCode(self, code, forceUpdate = False):
        """Update all sensors value from ir code and send xpl-trig."""
        states = self.cmdCode.decodeCodeBin(code, forceUpdate)
        print(states)
        states["current"].update(states["toUpdate"])
        for toUpd in states["current"] :
            self.cmdCode.setCmd(toUpd, states["current"][toUpd])
            self.sendSensorUpdate({toUpd: states["current"][toUpd]})
        self.cmdCode.isUpdate = True

    def handle_cmd_request(self, command, message):
        """Handle a cmd message from hub"""
        data = {'device': message['device_id']}
        cmd = ""
        find = False
        status = False
        reason = ""
        for cmd in message.keys() :
            if cmd not in ['command_id', 'device_id'] :
                break;
        if cmd == "" :
            self._log.debug(u"DaikinRemote object, unknown command : {0}".format(message))
            return False, False, u"DaikinRemote object, unknown command : {0}".format(message)
        print(u"handle_cmd_request {0} - {1}".format(cmd, message))
        if cmd == "send" :
            find = True
            callback = self.sendToIRdevice
            status = True
            reason = None
            data.update({'type': cmd, 'state': True})
            self._currentAck.append(data)
        else :
            value = message[cmd]
            for param in command['parameters'] :
                if param['key'] == cmd :
                    find = True
                    dt_Type = self._manager._Plugin.get_data_type(param['data_type'])
                    if dt_Type :
                        if 'labels' in dt_Type :
                            for k, v in dt_Type['labels'].iteritems():
                                if value == k or value == v :
                                    value = v
                                    break;
                        elif 'values' in dt_Type :
                            for k, v in dt_Type['values'].iteritems():
                                if value == k or value == v :
                                    value = v
                                    break;

                    value = message[cmd]
                    if cmd == 'setpoint': value = int(round(float(message[cmd])))
                    if self.cmdCode.setCmd(cmd, value) :
#                        callback = self.sendToIRdevice
                        callback = None
                        status = True
                        reason = None
                        data.update({'type': cmd, 'state': value})
                        self._currentAck.append(data)
                    else :
                        callback = None
                        status = False
                        reason = "Command {0} doesn't exist for remote : {1}".format(cmd, self.getRemoteId)
                    break
        return find, status, reason, callback

    def handle_sensor_pub(self, sensor, value):
        """Handle a sensor message from MQ"""
        if sensor :
            if sensor['reference'] == 'ack_ir_cmd' :
                if self._currentAck :
                    if value == 'ok':
                        for ack in self._currentAck :
                            if ack['type'] != 'send' :
                                print(u"Set ack sendor : {0}".format(ack))
                                if self.cmdCode.setCmd(ack['type'], ack['state']):
                                    self.sendSensorUpdate({ack['type']: ack['state']})
                    else :
                        self._log.debug(u"DaikinRemote object, Error on ack IRTrans message : {0}, Error : {1}".format(self._currentAck, value))
                    self._currentAck = []
                else :
                    self._log.debug(u"DaikinRemote object, unknown MQ ack : {0}".format(value))
            elif sensor['reference'] == 'code_ir':
                self._log.debug(u"DaikinRemote object receiver an IR Code.")
                self.udpateAllFromCode(value, not self.cmdCode.isUpdate)
            elif sensor['reference'] == 'power':
                self.cmdCode.setCmd('power', value)
                self.sendSensorUpdate({'power': value})
            else :
                self._log.debug(u"DaikinRemote object not recipient of reporting sensor :{0} with value : {1}".format(sensor, value))

if __name__ == "__main__":
    RemoteManager(None,  None)
