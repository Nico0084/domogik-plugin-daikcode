dmg_send xpl-cmnd daikin.basic "device=Remote_1,command=switch,datatype=BinTimings,power=On" 
sleep 5
dmg_send xpl-trig ir.basic "device=IRTrans_ws,type=ack_ir_cmd,result=ok"
