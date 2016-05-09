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

    def __init__(self, xplPlugin,  cb_send_xPL):
        """ Init manager remote objet
            @param log  : log instance
            @param cb_send_xPL : callback to send xpl msg
            @param stop : stop instance
        """
        self._xplPlugin = xplPlugin
        self._cb_send_xPL = cb_send_xPL
        self._stop = xplPlugin.get_stop()  # TODO : pas forcement util ?
        self.remotes ={} # list of daikin remote control object
        self._xplPlugin.log.info(u"Remote Manager is ready.")

    def addRemote(self, device):
        """Add a remote from domogik device"""
        name = getRemoteId(device)
        if self.remotes.has_key(name) :
            self._xplPlugin.log.debug(u"Remote Manager : remote {0} already exist, not added.".format(name))
            return False
        else:
            self.remotes[name] = DaikinRemote(self,  device,  self._xplPlugin.log)
            self._xplPlugin.log.info(u"Remote Manager : created new remote {0}.".format(name))
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
#        self._xplPlugin.log.debug (u"getIdsRemote check for device : {0}".format(idToCheck))
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
        self._xplPlugin.log.debug(u"getIdsRemote for '{0}' return : {1}".format(idToCheck, retval))
        return retval

    def refreshRemoteDevice(self,  remote):
        """Request a refresh domogik device data for a remote."""
        cli = MQSyncReq(zmq.Context())
        msg = MQMessage()
        msg.set_action('device.get')
        msg.add_data('type', 'plugin')
        msg.add_data('name', self._xplPlugin.get_plugin_name())
        msg.add_data('host', get_sanitized_hostname())
        devices = cli.request('dbmgr', msg.get(), timeout=10).get()
        for a_devices in devices:
            if a_device['device_type_id'] == remote._device['device_type_id']  and a_device['id'] == remote._device['id'] :
                if a_device['name'] != remote.device['name'] : # rename and change key remote id
                    old_id = getRemoteId(remote._device)
                    self.remotes[getRemoteId(a_device)] = self.remotes.pop(old_id)
                    self._xplPlugin.log.info(u"Remote {0} is rename {1}".format(old_id,  getRemoteId(a_device)))
                remote.updateDevice(a_device)
                break

    def sendXplAck(self,  data):
        """Send an ack xpl message"""
    #    self._xplPlugin.log.debug(u"Send ack {0}".format(data))
        self._cb_send_xPL("xpl-trig", "sensor.basic", data)

class DaikinRemote():
    """Remote control type Daikin object"""

    def __init__(self, manager,  device, log):
        """Init remote control type daikin"""
        self._manager = manager
        self._device = device
        self.cmdCode = CodeIRDaikin(self,  self._device['name'])
        self._log = log
        self._currentAck = None

    # On accède aux attributs uniquement depuis les property
    getRemoteId = property(lambda self: getRemoteId(self._device))
    getDomogikDevice = property(lambda self: self._getDomogikDevice())
    getIRDevice = property(lambda self: self._getIRDevice())

    def updateDevice(self,  device):
        """Update device data."""
        self._device = device

    def _getDomogikDevice(self):
        """Return device Id for xPL domogik device"""
        if self._device :
            # try to find in xpl_commands
            for a_cmd in self._device['xpl_commands']:
                for a_param in self._device['xpl_commands'][a_cmd]['parameters']:
                    if a_param['key'] == 'device' : return a_param['value']
            # try to find in xpl_stats
            for a_stat in self._device['xpl_stats']:
                for a_param in self._device['xpl_stats'][a_stat]['parameters']['static']:
                    if a_param['key'] == 'device' : return a_param['value']
            return None
        else : return None

    def _getDatatype(self):
        """Return datatype for xPL domogik device
            "1" : "BinTimings",
            "2" : "IR Raw",
            "3" : "IR Hexa"
        """
        if self._device :
            type = 'Unknown'
            if self._device['parameters']["datatype"]['value'] == "1" :
                type = "BinTimings"
            elif self._device['parameters']["datatype"]['value'] == "2" :
                type = "IR Raw"
            elif self._device['parameters']["datatype"]['value'] == "3" :
                type =  "IR Hexa"
            return type
        else : return None

    def _getIRDevice(self):
        """Return IRDevice for IRTrans."""
        if self._device : return self._device['parameters']["irdevice"]['value']
        else : return ""

    def sendToIRdevice(self):
        """Send xpl-cmnd to IRTrans Transmitter."""
        # TODO : gérer les datatypes
        data = {"device":  self._device['parameters']["irdevice"]['value'],  "command": "send",  "datatype": self._getDatatype()}
        if self._getDatatype() == "BinTimings" :
            data["code"] = self.cmdCode.encodeCmdIRTrans()
            data["timing"] = self.cmdCode.timing.encodeTimingIRTrans()
            self._manager._cb_send_xPL("xpl-cmnd", "irtrans.basic",  data)
        else : self._log.info (u"datatype : {0} not handled, xpl-cmnd to IR transmitter not send.".format(self._getDatatype()))

    def sendDomogikXplUpdate(self, item):
        """Send xpl-trig to domogik device."""
        data =  {"device": self.getDomogikDevice}
        for cmd in item :
            data.update({'type' :  cmd})
            if cmd in ['power', 'vertical-swing', 'horizontal-swing', 'powerfull', 'silent',  'home-leave',  'sensor'] :
               data.update({'state': item[cmd]})
            elif cmd == 'setmode' :
                data.update({'mode': item[cmd]})
            elif cmd == 'setpoint' :
                data.update({'temp': item[cmd]})
            elif cmd == 'speedfan' :
                data.update({'speed': item[cmd]})
            elif cmd in ['datetime', 'starttime',  'stoptime'] :
                data.update({'time': self.cmdCode.formatStrDelais(item[cmd])})
            else :
                data.update({cmd: item[cmd]})
        self._manager._cb_send_xPL('xpl-trig', 'sensor.basic',  data)

    def udpateAllFromCode(self, code):
        """Update all sensors value from ir code and send xpl-trig."""
        states = self.cmdCode.decodeCodeBin(code)
        states["current"].update(states["toUpdate"])
        for toUpd in states["current"] :
            self.cmdCode.setCmd(toUpd, states["current"][toUpd])
            self.sendDomogikXplUpdate({toUpd: states["current"][toUpd]})
        self.cmdCode.isUpdate = True

    def handle_xpl_cmd(self,  xPLmessage):
        """Handle a xpl-cmnd message from hub"""
        data = {'device': xPLmessage['device']}
        if xPLmessage['command'] == 'switch' :
            if xPLmessage.has_key('power') : cmd = 'power'
            elif xPLmessage.has_key('vertical-swing') : cmd = 'vertical-swing'
            elif xPLmessage.has_key('horizontal-swing') : cmd = 'horizontal-swing'
            elif xPLmessage.has_key('powerfull') : cmd = 'powerfull'
            elif xPLmessage.has_key('silent') : cmd = 'silent'
            elif xPLmessage.has_key('home-leave') : cmd = 'home-leave'
            elif xPLmessage.has_key('sensor') : cmd = 'sensor'
            else :
                self._log.debug(u"DaikinRemote object, unknows xPL command : {0}".format(xPLmessage))
                return
            if self.cmdCode.setCmd(cmd, xPLmessage[cmd]) :
                self.sendToIRdevice();
                value = xPLmessage[cmd]
            else : value = self.cmdCode.getCmd(cmd)["value"]
            data.update({'type': cmd,  'state': value})
        elif xPLmessage['command'] == 'setpoint':
            if self.cmdCode.setCmd("setpoint", int(xPLmessage['temp'])) :
                self.sendToIRdevice();
                value = xPLmessage['temp']
            else : value = self.cmdCode.getCmd("setpoint")["option"]
            data.update( {'type': "setpoint",  'temp': value})
        elif xPLmessage['command'] == 'setmode':
            if self.cmdCode.setCmd("setmode", xPLmessage["mode"]) :
                self.sendToIRdevice();
                value = xPLmessage['mode']
            else : value = self.cmdCode.getCmd("setmode")["value"]
            data.update({'type': "setmode",  'mode': value})
        elif xPLmessage['command'] == 'speedfan':
            if self.cmdCode.setCmd("speedfan", xPLmessage["speed"]) :
                self.sendToIRdevice();
                value = xPLmessage['speed']
            else : value = self.cmdCode.getCmd("speedfan")["value"]
            data.update({'type': "speedfan",  'speed': value})
        elif xPLmessage['command'] == 'settime':
            if xPLmessage.has_key('starttime') : cmd = 'starttime'
            elif xPLmessage.has_key('stoptime') : cmd = 'stoptime'
            elif xPLmessage.has_key('datetime') :
                cmd = 'datetime' # TODO : to handle in daikin codage rpi
                self._log.debug(u"DaikinRemote object, date time set not handled actually.")
                return
            if self.cmdCode.setCmd(cmd, xPLmessage[cmd]):
                self.sendToIRdevice();
                value = xPLmessage[cmd]
            else :
                self._log.debug(u"DaikinRemote object, unknows time definition in xPL command : {0}".format(xPLmessage))
                value = self.cmdCode.getCmd(cmd)["option"]
            data.update({'type': "time",  'time': value})
        else :
            self._log.debug(u"DaikinRemote object, unknows xPL command : {0}".format(xPLmessage))
            return
#        self._manager.sendXplAck(data)
        self._currentAck = data

    def handle_xpl_trig(self, message):
        """Handle a xpl-trig message from hub"""
        if message.has_key('type'):
            if message.has_key('device'):
                if message['type'] == 'ack_ir_cmd' and message['device'] == self.getIRDevice :
                    if self._currentAck :
                        if message['result'] == 'ok':
                            self._manager.sendXplAck(self._currentAck)
                        else :
                            self._log.debug(u"DaikinRemote object, Error on ack IRTrans message : {0}, Error : {1}".format(self._currentAck,  message['result']))
                        self._currentAck =None
                    else :
                        self._log.debug(u"DaikinRemote object, unknows xPL Ack trig : {0}".format(message))
                elif message['type'] == 'code_ir':
                    self._log.debug(u"DaikinRemote object receiver an IR Code.")
                    if not self.cmdCode.isUpdate :
                        self.udpateAllFromCode(message['code'])
                    else :
                        states = self.cmdCode.decodeCodeBin(message['code'])
                        for toUpd in states["toUpdate"] :
                            self.cmdCode.setCmd(toUpd, states["toUpdate"][toUpd])
                            self.sendDomogikXplUpdate({toUpd: states["toUpdate"][toUpd]})
                elif message['type'] == 'power' and message['device'] == self.getIRDevice :  # En cas de reception de state depuis le IRDevice.
                    self.cmdCode.setCmd(message['type'], message['state'])
                    self.sendDomogikXplUpdate({message['type']: message['state']})
                else :
                    self._log.debug(u"DaikinRemote object not recipient of xpl-trig :{0}".format(message))
            else :
                self._log.debug(u"DaikinRemote object receiver unknown xpl-trig message : {0}".format(message))

if __name__ == "__main__":
    RemoteManager(None,  None)
