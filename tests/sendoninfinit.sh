
while true
do
    dmg_send xpl-cmnd daikin.basic "device=Remote_1,command=switch,datatype=BinTimings,power=Off" 
    sleep 3
done
