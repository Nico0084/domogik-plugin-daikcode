dmg_send xpl-cmnd daikin.basic "device=Remote_1,command=setmode,datatype=BinTimings,mode=Cool" 
sleep 5
dmg_send xpl-trig ir.basic "device=IRTrans_ws,type=ack_ir_cmd,result=ok"
sleep 20
dmg_send xpl-cmnd daikin.basic "device=Remote_1,command=setmode,datatype=BinTimings,mode=Auto" 
sleep 5
dmg_send xpl-trig ir.basic "device=IRTrans_ws,type=ack_ir_cmd,result=ok"
