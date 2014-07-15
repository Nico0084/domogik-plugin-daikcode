# -*- coding: utf-8 -*-

def from_switch_to_DT_Switch(x):
    if x == 'Off':
        print "+++ from_switch_to_DT_Switch : {0} to {1}".format(x,  0)        
        return int(0)
    if x == 'On':
        print "+++ from_switch_to_DT_Switch : {0} to {1}".format(x,  1)
        return int(1)
