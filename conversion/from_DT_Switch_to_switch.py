# -*- coding: utf-8 -*-

def from_DT_Switch_to_switch(x):
    if x == '0':
        print "+++ from_DT_Switch_to_switch : {0} to {1}".format(x,  'Off')        
        return 'Off'
    if x == '1':
        print "+++ from_DT_Switch_to_switch : {0} to {1}".format(x, 'On')        
        return 'On'
