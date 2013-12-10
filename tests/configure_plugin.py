#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
REST_URL="http://192.168.1.195:40405"
HOST="vmdomogik0"
PLUGIN_NAME="daikcode"
DEVICE_ADDRESS="/home"      
########################################################

import zmq
from zmq.eventloop.ioloop import IOLoop
from domogik.mq.reqrep.client import MQSyncReq
from domogik.mq.message import MQMessage



def configure_plugin():
    """Configure plugin with mq request"""
    cli = MQSyncReq(zmq.Context())
    msg = MQMessage()
    msg.set_action('config.set')
    msg.add_data('type', 'plugin')
    msg.add_data('host', HOST)
    msg.add_data('name', PLUGIN_NAME)
    msg.add_data('data', {'auto_startup' : False})
    print 'Set plugin configuration ',  msg.get()
    print cli.request('dbmgr', msg.get(), timeout=10).get() 
    
    msg.set_action('config.get')
    print 'Get configuration',  msg.get()
    print cli.request('dbmgr', msg.get(), timeout=10).get() 
    
if __name__ == "__main__":
    configure_plugin()

