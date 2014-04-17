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
import os

# Class objet de codage des codes télécommande Pompe à chaleur DAIKIN

codeConst = "210001000010110111110010000001111000000000000000000000000010000003"
#cmdsDaikin = ['Inconnue','Pulse de start','ON/OFF','Mode Fonctionnement','Température','Ventilation battante verticale','Vitesse de ventilation','Ventilation battante horizontale',
#'Heure départ','Heure de fin','Mode powerful','Mode silencieux','Home leave','Sensor','Code de vérification']
cmdsDaikin = ['Unknown','Pulse start','power','setmode','setpoint','vertical-swing','speedfan','horizontal-swing',
                    'starttime','stoptime','powerfull','silent','home-leave','sensor','Checksun']

class DaikinCodeException(Exception):
    """"DaikinCode lib exception  class"""

    def __init__(self, value):
        self.msg = "DaikinCode lib exception : " + value
        Exception.__init__(self, self.msg)

class CmdDaikin:
    """Définition d'une commande type daikin"""
    def __init__(self, cmd, offset, dim, ordres, ordDef, opt =0):
        """Déclaration d'une commande"""
        self.cmd = cmd                     # nom de la commande
        self.offset = offset                # offset dans le code complet
        self.dim = dim                       # longueur de bit de codage
        self.ordres = ordres                # Liste des ordres et les correspondance en codage
        self.ordC = ordDef                  # Ordres par défaut
        self.opt = opt

    def posFin (self):
        """Renvoi la position de fin """
        return self.offset + self.dim

    def getIRCode (self, ordre = "", opt = 0):
        """Renvoi le code IR en fonction de la commande et de l'ordre \
            Doit-être appelé par la méthode de la class CodeIRDaikin.buildBinCodeIR() \
            pour géré les exceptions des températures."""
        cir=""
        if ordre == "" : ordre = self.ordC
        if self.cmd == cmdsDaikin [0] :             # c'est une commande inconnue
                cir = self.ordres[""]
        elif self.cmd == cmdsDaikin [4] or self.cmd == cmdsDaikin [8] or self.cmd == cmdsDaikin [9]:   # c'est une température, l'heure de départ, l'heure de fin.
                cir=bin(opt)[2:]            # codage binaire de opt
                if len(cir) < self.dim :    # La température ou en minutes depuis l'heure courant entre 0 et 1440 mns (24h00)
                    while int((self.dim)) - len(cir) > 0 :
                           cir ='0' + cir
                cir = cir[::-1]                # Reverse pour codage DAIKIN
        elif ordre in self.ordres.keys() :            # Toute autre commande codée dans le dictionnaire
                cir = self.ordres[ordre]
        return cir

    def LabelEtatCmd (self, opt = -1) :
        """Retroune l'état de la commande utilisateur sous forme de dictionnaire \
           Doit-être appelé par la méthode de la class CodeIRDaikin.LabelEtatCmds() \
           pour géré les exceptions des températures."""
        eC ={}
        if self.cmd == cmdsDaikin [0] : eC= {}                                     # c'est une commande inconnue
        elif self.cmd == cmdsDaikin [1] : eC= {}                                  # c'est le pulse start
        elif self.cmd == cmdsDaikin [4]  :                                             # c'est la température
            if opt == -1 : eC = {self.cmd: self.opt}                   # La température
            else : eC = {self.cmd: opt }                                     # Exception : La température forcée en option
        elif self.cmd == cmdsDaikin [8] or self.cmd == cmdsDaikin [9] :   # c'est l'heure de départ ou l'heure de fin.
            eC = {self.cmd: self.opt}                          # en minutes depuis l'heure courant entre 0 et 1440 mns (24h00)
        elif self.cmd == cmdsDaikin [14] : eC= {}                                  # c'est le cheksum
        else : eC = {self.cmd: self.ordC}            # Toute autre commande utilisateur codée dans le dictionnaire.
        return eC

    def setCurrentValue (self, ord, opt = 0):
        """Définis l'ordre et l'option courant puis renvoi le code IR"""
        print "update current cmd {0}: {1},  {2}".format(self.cmd,  ord,  opt)
        self.ordC = ord
        self.opt = opt
        return self.getIRCode (ord, self.opt)

    def extractOrdFromBinCode(self, code):
        """Décode l'ordre depuis un code 'binaire sans codeConst'"""
        val = code[self.offset:self.posFin()]
        print "\nCommande {0}, valeur extraite : {1}".format(self.cmd, val)
        for ord in self.ordres :
            if ord == "Bin2Num":
                val = "0b" + val[::-1] 
                print val
                val = int(val, 2)
                print "Etat : {0} ({1} / {2})".format(ord,  val,  self.opt)
                return val
            elif val == self.ordres[ord] :
                print "Etat : {0} ({1} / {2})".format(ord,  val,  self.opt)
                return ord
        print "not find {0}".format(self.cmd)
        return None

class Timing:
    """Timing, pulse et pause"""
    def __init__ (self, li="" ):
        "Init de l'objet, valeur par défauts type IRtrans."
        self.num = 0        # Numéro du timing
        self.nbt = 0         # nombre de valeurs de time du timing
        self.timings=[]     # Listes des timings pair pulse/pause en micro sec.
        self.rc = 0          # Nombre de répétition
        self.rp = 0          # pause entre de répétition en ms
        self.fl = 0           # longueur de cadre du signal IR (remplace rp)
        self.freq = 0       # fréquence du signal (0 + pas de modulation)
        self.sb = 0         # code du bit de start (startbit)
        self.rs = 0          # le startbit est répété
        self.rc5 = 0        # RC5 code (pas besoin de timing)
        self.rc6 = 0        # RC6 code (pas besoin de timing)
        self.notog = 0     # RC5 / RC6 toggle bit non utilisé
        if li !="" : self.decodeTimingITRrans(li)
        else : self.setDict({'NUM':0, 'N': 4, 'FREQ': 38, 'FL': 0, 'RP': 0, 'RS': 0, 'RC5': 0, 'RC6': 0, 'RC': 1, 'NOTOG': 0, 'SB': 0, 
                                   'TIMINGS': [['440', '448'], ['440', '1288'], ['3448', '1720'], ['408', '29616']] })

    def decodeTimingITRrans (self, li):
        """Décode les informations de timing type IRTrans, issues d'un fichier IRTrans. \
            Ligne entière du fichier"""
        if li != "\n" :                                          # C'est un timing à décoder
             l1 = li.split('[')                                 # découpage des paramètres
             self.num = int(l1[1].partition(']')[0])    # Récupération du numéro de timing
             l1 = l1[2:]
             for l2 in l1 :                                        # Balayage du décodage
                 l3 = l2.split(']')
                 if l3[0]   == 'N' :       self.nbt = int(l3[1])
                 elif l3[0] == 'RC' :     self.rc = int(l3[1])
                 elif l3[0] == 'RP' :     self.rp = int(l3[1])
                 elif l3[0] == 'FL' :     self.fl = int(l3[1])    
                 elif l3[0] == 'FREQ' :  self.freq = int(l3[1])
                 elif l3[0] == 'SB' :     self.sb = int(l3[1])
                 elif l3[0] == 'RS' :     self.rs = int(l3[1])
                 elif l3[0] == 'RC5' :    self.rc5 = int(l3[1])
                 elif l3[0] == 'RC6' :    self.rc6 = int(l3[1])
                 elif l3[0] == 'NOTOG' : self.notog = int(l3[1])
                 else :
                     try :
                         int(l3[0])
                         self.timings.append (l3[1].split(' '))
                     except ValueError:
                         False
             return self    

    def encodeTimingIRTrans(self):      
        """Encode les informations de timing sous format IRTrans, pour inclure dans un fichier."""
        li ='  [%d][N]%d' %(self.num,  self.nbt)
        n = 1
        for a in self.timings :
            li = li +'[%d]%s %s' %(n,  a[0],  a[1])
            n= n + 1
        li = li + '[RC]%d' %(self.rc)
        if self.fl !=0 : li = li + '[FL]%d' %(self.fl)
        else : li = li + '[RP]%d' %(self.rp)
        li = li + '[FREQ]%d' %(self.freq)
        if self.sb !=0 : li = li + '[SB]%d' %(self.sb)
        if self.rs !=0 : li = li + '[RS]%d' %(self.rs)
        if self.rc5 !=0 : li = li + '[RC5]%d' %(self.rc5)
        if self.rc6 !=0 : li = li + '[RC6]%d' %(self.rc6)
        if self.notog !=0 : li = li + '[NOTOG]%d' %(self.notog)
        li = li + '\n'
        return li

    def display (self):
        """Affiche les valeurs de paramètres du timing"""
        print "timing number :", self.num       
        print "     number of timing values: ", self.nbt 
        print "     pair pulse/pause timings liste in micro sec. :", self.timings
        print "     repeat number : ", self.rc
        print "     pause between repeat in ms : ", self.rp
        print "     frame length of the IR signal (replaces rp) : ", self.fl
        print "     frequency signal (0 + no modulation) : ", self.freq
        print "     start bit code (startbit) : ", self.sb
        print "     repeated startbit : ", self.rs
        print "     RC5 code (no need timing) : ", self.rc5
        print "     RC6 code (no need timing) : ", self.rc6
        print "     RC5 / RC6 toggle bit not use : ", self.notog

    def getDict (self):
        """Retourne les valeurs sous forme de dict"""
        return {
            'N' : self.nbt, 
            'RC' : self.rc,
            'RP' : self.rp,
            'FL' : self.fl,
            'FREQ' : self.freq,
            'SB' : self.sb,
            'RS' : self.rs,
            'RC5' : self.rc5, 
            'RC6' : self.rc6, 
            'NOTOG' : self.notog,
            'TIMINGS' : self.timings
            }

    def setDict(self,  timing):
        """Affecte le valeur du timming à la class."""
        try : 
            self.nbt = timing['N']
            self.rc = timing['RC']
            self.rp = timing['RP']
            self.fl = timing['FL']
            self.freq = timing['FREQ']
            self.sb = timing['SB']
            self.rs = timing['RS']
            self.rc5 = timing['RC5']
            self.rc6 = timing['RC6']
            self.notog = timing['NOTOG']
            self.timings = timing['TIMINGS']
        except:
           raise  DaikinCodeException('Bad Timming format : {0}'.format(timing))

class Timings :
    """Liste des timings (pulses et pauses)"""
    def __init__ (self ):
        self.lstTimings = []   # Suite des timings

    def append (self,timing):
        """Ajoute un timing à la liste"""
        self.lstTimings.append (timing)

    def litFichIRTrans (self, fichier):
        """lit les timings d'un fichier type IRTrans"""
        try:
            fich = open (fichier,'r')
        except :
            print 'error ouverture fichier : ', fichier
            return 0
        else :
            while 1:
                li = fich.readline ()
                if li == "" :
                    break
                elif li=="[TIMING]\n" :
                    li = fich.readline ()                                # Lecture de la partie timing du fichier
                    while li != "[COMMANDS]\n"  :                 # Fin de la partie timing
                        if li != "\n" :                                    # C'est un timing à décoder
                            self.lstTimings.append(Timing(li))     # Ajout timing avec décodage de la ligne
                        li = fich.readline ()
    
    def encodeTimingsIRTrans(self) :
        """Encode les timings pour fichier IRTRans"""
        code =''
        for t in self.lstTimings:
            code = code + t.encodeTimingIRTrans()
        return code

class CodeIRDaikin :
    """Liste de cmd daikin pour gestion du code complet """
    def __init__ (self,  nom ='test',  timing = Timing() ):
        self.lstCmds = []     # Suite des commandes à enchainer
        self.nom =nom        # Nom de la commande
        self.timing=timing    # timing utilisé
        
        self.lstCmds.append (CmdDaikin (cmdsDaikin [1], 0, 1, {"0" : "2","1" : "5"}, "0"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 1, 40, {"" : "1000100001011011111001000000000000000000"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [2], 41, 1, {"Off" : "0","On" : "1"}, "Off"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 42, 3, {"" : "000"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [3], 45, 3, {"Auto" : "000",\
                                                                                    "Heat" : "001",\
                                                                                    "Fan only" : "011",\
                                                                                    "Dry" : "010",\
                                                                                    "Cool" : "110"}, "Heat"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 48, 2, {"" : "00"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [4], 50, 7, {"Bin2Num" : "011010"}, "Bin2Num"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 57, 8, {"" : "00000000"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [5], 65, 4, {"Off" : "0000","On" : "1111"},"On"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [6], 69, 4, {"Unknown" : "0000",\
                                                                                    "Auto" : "0101",\
                                                                                    "Lower" : "1101",\
                                                                                    "Speed 1" : "1100",\
                                                                                    "Speed 2" : "0010",\
                                                                                    "Speed 3" : "1010",\
                                                                                    "Speed 4" : "0110",\
                                                                                    "Speed 5" : "1110"}, "Auto"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [7], 73, 4, {"Off" : "0000","On" : "1111"}, "Off"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 77, 4, {"" : "0000"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [8], 81, 12, {"Bin2Num" : "000000000000"}, "Bin2Num"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [9], 93, 12, {"Bin2Num" : "000000000000"}, "Bin2Num"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [10], 105, 1, {"Off" : "0","On" : "1"}, "Off"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 106, 4, {"" : "0000"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [11], 110, 1, {"Off" : "0","On" : "1"}, "Off"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 111, 1, {"" : "0"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [12], 112, 1, {"Off" : "0","On" : "1"}, "Off"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 113, 17, {"" : "00000000000000110"},  ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [13], 130, 1, {"Off" : "0","On" : "1"}, "Off"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 131, 14, {"" : "00000000000000"}, ""))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [14], 145, 8, {"Cheksum" : "00000000"}, "Cheksum"))
        self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 153, 1, {"" : "0"}, ""))
       
    def append (self, cmd):     # Ajout d'une commande avec ses paramètres
        """Ajoute une commande à la collection"""
        self.lstCmds.append (cmd)
            
    def buildBinCodeIR (self): 
        """Génère le code IR complet en fonction des valeurs courantes d'ordre, retourne une string de code binaire."""
        modExcept = {"Fan only" : 25,  "Dry" : 96}  # Valeurs corrigées en cas d'exception
        code=""
        for cmd in self.lstCmds :
            ord =""
            opt =0
            if cmd.cmd == cmdsDaikin[4] :               # Exception pour les modes Ventillation et Condensation, la température doit-être imposée.
                mode = self.lstCmds[self.indexCmd(cmdsDaikin[3])].ordC              # récupération du mode de chauffage
                if mode in modExcept.keys():                                                    # si dans un mode d'exception -> forcer température
                    ord = "Bin2Num"
                    opt = modExcept[mode]
            code = code + cmd.getIRCode (ord,  opt)
        code = self.cheksum(codeConst + code)
        return code
            
    def buildRawCodeIR (self): 
        """Génère le code IR complet en fonction des valeurs courantes d'ordre,
            retourne dict avec un tableau de code RAW avec les paires pulse/pause."""
        codeB = self.buildBinCodeIR()
        codeR ={'FREQ': self.timing.freq,  'PAIRS' : []}
        for t in codeB : codeR['PAIRS'].append(self.timing.timings[int(t)])
        return codeR
            
    def indexCmd (self,  cmd):
        """Retourne l'index, dans la liste de commande, d'une commande particulière"""
        for id in range(0,len(self.lstCmds )):
            if self.lstCmds[id].cmd == cmd :
                return id
                break
        return -1
                    
    def setCmd (self, cmd, value):  
        """Configure une commande de la liste"""
        id = self.indexCmd(cmd)
        if id != -1 :
            if cmd in [cmdsDaikin[4], cmdsDaikin [8] , cmdsDaikin [9]] :   
                ordre = "Bin2Num"
                opt = value
            else :
                ordre =value
                opt = 0
            self.lstCmds[id].setCurrentValue(ordre, opt)
            return True       
        else :
            return False
            
    def getCmd (self,  cmd = cmdsDaikin [0]):  
        """Retourne l'etat d'une commande dous forme de dict {value, option}"""
        try :
            return {"value": self.lstCmds[self.indexCmd(cmd)].ordC ,  "option" : self.lstCmds[self.indexCmd(cmd)].opt}   
        except ValueError :
            raise DaikinCodeException(u"Unknows command {0}".format(cmd))


    def cheksum (self,  code):
        """Calcul le checksum d'un code complet avec le code constructeurinclue (codeConst) et y insert le cheksum"""
        c = self.lstCmds[self.indexCmd(cmdsDaikin [14])]     # récupération des valeurs de positions
        lgC = len(codeConst)
        posChk = c.offset + lgC
        chk = 0
        dataC = code[lgC +1 : posChk]                # extraction de la partie util au calcul du cheksum
        for i  in range (0, len(dataC), 8):             # extraction par pas de 8 bits
            chk=chk + int (dataC[i:i+8][::-1], 2)    # addition des bytes après reverse bits
        print chk
        return code[0:posChk] + bin(chk)[::-1][0:c.dim] + code[posChk +c.dim:]   # reconstruction de code complet
    
    def labelEtatCmds (self) :
        """Retorune uniquement l'état des commandes utilisateur sous forme liste de dictionnaire"""
        modExcept = {"Fan only" : 25,  "Dry" : 96}   # Valeurs corrigées en cas d'exception
        etatC = {}
        for cmd in self.lstCmds:
            opt = -1
            if cmd.cmd == cmdsDaikin[4] :               # Exception pour les modes Ventillation et Condensation, la température doit-être imposée.
                mode = self.lstCmds[self.indexCmd(cmdsDaikin[3])].ordC                # récupération du mode de chauffage
                if mode in modExcept.keys():                                                    # si dans un mode d'exception -> forcer température
                    opt = modExcept[mode]
            lab = cmd.LabelEtatCmd(opt)
            if lab !={} : etatC.update(lab)
        return etatC
            
    def encodeCmdIRTrans(self):
        """Encode en ligne ASCII la commande pour format fichier IRTrans"""
#            return  '[T]%d[D]%s' %(self.timing.num,  self.buildBinCodeIR ())
        return  self.buildBinCodeIR()

    def decodeCodeBin(self,  codeC):
        """Decode un code 'binaire' entier (avec le codeConst DAIKIN) et renvoie un dict des valeurs courantes et à mettre à jour."""
        lgC = len(codeConst)
        code = codeC[lgC:]
        print code
        cmdsState = self.labelEtatCmds()
        print cmdsState
        change ={}
        for cmd in self.lstCmds:
            state = cmd.extractOrdFromBinCode(code)
            if state != None :
                if cmdsState.has_key(cmd.cmd) :
                    if cmdsState[cmd.cmd] != state:
                        print "Valeur changée, à updater. {0} / {1}".format(cmdsState[cmd.cmd],  state)
                        change.update({cmd.cmd: state})
                    else :
                        print "Valeur à jour."
                else : print "Commande non implémentée."
        return {'current': cmdsState,  'toUpdate' : change}
                
if __name__ == '__main__' :
    cmds = CodeIRDaikin()
    a, nb = 0, 23
    while a < nb :
        print cmds.lstCmds[a].cmd, " --> ", cmds.lstCmds[a].ordC
        a=a+1
    print cmds.buildBinCodeIR ()                 
    tims = Timings()
    tims.litFichIRTrans("..\data\Daikin.rem")
    for t in tims.lstTimings : 
        print t.getDict()
        t.setDict({'TIMINGS': [['440', '448'], ['440', '1288'], ['3448', '1720'], ['408', '29616']], 'N': 4, 'FREQ': 38, 'FL': 0, 'RP': 0, 'RS': 0, 'RC5': 0, 'RC6': 0, 'RC': 1, 'NOTOG': 0, 'SB': 0})
    print cmds.buildRawCodeIR()
    cmds.setCmd("setmode","Fan only")
    cmds.setCmd("power","On")
    cmds.setCmd("setpoint", 35)
    cmds.setCmd("vertical_swing", "On")
    cmds.setCmd("speedfan", "Auto")
    print cmds.buildBinCodeIR ()
    for lab in cmds.labelEtatCmds() :
        print lab.keys(),  lab.values()

    print tims.encodeTimingsIRTrans()
    print cmds.encodeCmdIRTrans()
