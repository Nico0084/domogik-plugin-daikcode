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
from zmq.eventloop.ioloop import IOLoop
from domogik.mq.reqrep.client import MQSyncReq
from domogik.mq.message import MQMessage
from domogik.common.utils import get_sanitized_hostname
from domogik_packages.plugin_daikcode.lib.daikin_encode import CodeIRDaikin
import pprint
    
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
            print "Add remote :"
            pprint.pprint(device)
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
        self._xplPlugin.log.debug (u"getIdsRemote check for device : {0}".format(idToCheck))
        if isinstance(idToCheck,  DaikinRemote) :
            for id in self.remotes.keys() :
                if self.remotes[id] == idToCheck :
                    retval = [id]
                    break
        else :
            self._xplPlugin.log.debug (u"getIdsRemote,  no DaikinRemote instance...")
            if isinstance(idToCheck,  str) :  
                findId = idToCheck
                self._xplPlugin.log.debug (u"str instance...")
            else :
                if isinstance(idToCheck,  dict) :
                    if idToCheck.has_key('device') : findId = idToCheck['device']
                    else :
                        if idToCheck.has_key('name') and idToCheck.has_key('id'): 
                            findId = getRemoteId(idToCheck)
            if self.remotes.has_key(findId) : 
                retval = [findId]
                self._xplPlugin.log.debug (u"key id type find")
            else :
                self._xplPlugin.log.debug (u"No key id type, search {0} in devices {1}".format(findId, self.remotes.keys()))
                for id in self.remotes.keys() :
                    self._xplPlugin.log.debug(u"Search in list by device key : {0}".format(self.remotes[id].getDomogikDevice))
                    if self.remotes[id].getDomogikDevice == findId : 
                        self._xplPlugin.log.debug('find remote :)')
                        retval.append(id)
        self._xplPlugin.log.debug(u"getIdsRemote result : {0}".format(retval))
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
        self.cmdCode = CodeIRDaikin(self._device['name'])
        self._log = log
             
    # On accède aux attributs uniquement depuis les property
    getRemoteId = property(lambda self: getRemoteId(self._device))
    getDomogikDevice = property(lambda self: self._getDomogikDevice())

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
        """Return datatype for xPL domogik device"""
        if self._device :
            return self._device['parameters']["datatype"]['value']
        else : return None
        
    def sendToIRdevice(self):
        """Send xpl-cmnd to IRTrans Transmitter."""
        # TODO : gérer les datatypes
        data = {"device":  self._device['parameters']["irdevice"]['value'],  "command": "send",  "datatype": self._getDatatype()}
        if self._getDatatype() == "BinTimings" :
            data["code"] = self.cmdCode.encodeCmdIRTrans()
            data["timing"] = self.cmdCode.timing.encodeTimingIRTrans()
            self._manager._cb_send_xPL("xpl-cmnd", "irtrans.basic",  data)
        else : self._log.info (u"datatype : {0} not handled, xpl-cmnd to IR transmitter not send.".format(self._getDatatype()))
    
    def handle_xpl_cmd(self,  xPLmessage):
        """Handle a xpl-cmnd message from hub"""
        data = {'device': xPLmessage['device'],  'datatype': xPLmessage['datatype']}
        if xPLmessage['command'] == 'switch' :
            if xPLmessage.has_key('power') : cmd = 'power'
            elif xPLmessage.has_key('vertical-swing') : cmd = 'vertical-swing'
            elif xPLmessage.has_key('horizontal-swing') : cmd = 'horizontal-swing'
            elif xPLmessage.has_key('powerfull') : cmd = 'powerfull'
            elif xPLmessage.has_key('silent') : cmd = 'silent'
            elif xPLmessage.has_key('home-leave') : cmd = 'home-leave'
            elif xPLmessage.has_key('sensor') : cmd = 'sensor'
            else : 
                self._log.debug("DaikinRemote object, unknows xPL command : {0}".format(xPLmessage))
                return
            if xPLmessage[cmd] == 'on': val = "ON"
            else : val = "OFF"
            if self.cmdCode.setCmd(cmd, val) :
                self.sendToIRdevice();
                value = xPLmessage[cmd]
            else : value = self.cmdCode.getCmd(cmd)["value"]
            data.update({'type': "switch",  'state': value})
        elif xPLmessage['command'] == 'setpoint':
            if self.cmdCode.setCmd("setpoint", opt = int(xPLmessage['temp'])) :
                self.sendToIRdevice();
                value = xPLmessage['temp']
            else : value = self.cmdCode.getCmd("setpoint")["option"]
            data.update( {'type': "setpoint",  'temp': value,  'zone': xPLmessage['zone']})
        elif xPLmessage['command'] == 'setmode':
            if self.cmdCode.setCmd("setmode", xPLmessage["mode"]) :
                self.sendToIRdevice();
                value = xPLmessage['mode']
            else : value = self.cmdCode.getCmd("setmode")["value"]
            data.update({'type': "mode",  'mode': value})
        elif xPLmessage['command'] == 'speedfan':
            if self.cmdCode.setCmd("speedfan", xPLmessage["speed"]) :
                self.sendToIRdevice();
                value = xPLmessage['speed']
            else : value = self.cmdCode.getCmd("speedfan")["value"]
            data.update({'type': "fan-speed",  'speed': value})
        elif xPLmessage['command'] == 'settime':
            if xPLmessage.has_key('starttime') : cmd = 'starttime'
            elif xPLmessage.has_key('stoptime') : cmd = 'stoptime'
            if self.cmdCode.setCmd(cmd, opt = xPLmessage[cmd]):
                self.sendToIRdevice();
                value = xPLmessage[cmd]
            else : 
                self._log.debug("DaikinRemote object, unknows time definition in xPL command : {0}".format(xPLmessage))
                value = self.cmdCode.getCmd(cmd)["option"]
            data.update({'type': "time",  'time': value})
        else : 
            self._log.debug("DaikinRemote object, unknows xPL command : {0}".format(xPLmessage))
            return
        self._manager.sendXplAck(data)
            
if __name__ == "__main__":
    RemoteManager(None,  None)
