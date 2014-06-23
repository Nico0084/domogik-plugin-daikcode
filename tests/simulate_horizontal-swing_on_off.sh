dmg_send xpl-cmnd daikin.basic "device=Remote_1,command=switch,datatype=BinTimings,horizontal-swing=On" 
sleep 5
dmg_send xpl-trig ir.basic "device=IRTrans_ws,type=ack_ir_cmd,result=ok"
sleep 20
dmg_send xpl-cmnd daikin.basic "device=Remote_1,command=switch,datatype=BinTimings,horizontal-swing=Off" 
sleep 5
dmg_send xpl-trig ir.basic "device=IRTrans_ws,type=ack_ir_cmd,result=ok"
