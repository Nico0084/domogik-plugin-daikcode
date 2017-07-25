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
from datetime import datetime, timedelta
import threading

# Class objet de codage des codes télécommande Pompe à chaleur DAIKIN

codeConst = "210001000010110111110010000001111000000000000000000000000010000003"
cmdsDaikin = ['Unknown','Pulse start','power','mode','setpoint','vertical_swing','speedfan','horizontal_swing',
                    'starttime','stoptime','powerfull','silent','home_leave','sensor','Checksun']

class DaikinCodeException(Exception):
    """"DaikinCode lib exception  class"""

    def __init__(self, value):
        self.msg = "DaikinCode lib exception : " + value
        Exception.__init__(self, self.msg)

class TimerDaikin:
    """Class permettant de gérer le starttime et stoptime de la PAC."""
    def __init__(self, tempo, duration, cbTempo, cbEnd, args= [], kwargs={}):
        self._cbTempo = cbTempo
        self._cbEnd = cbEnd
        self._args = args
        self._kwargs = kwargs
        self._tempo = tempo
        self._started = None
        self._duration = duration

    def _run(self):
        self._timer = threading.Timer(self._tempo, self._run)
        self._timer.start()
        duration = int(self._duration - ((timedelta.total_seconds(datetime.now() - self._started)) / 60))
        if duration <= 0 :
            self.stop()
            self._cbEnd(*self._args)
        else : self._cbTempo(duration,  *self._args)

    def start(self):
        self._timer = threading.Timer(self._tempo, self._run)
        self._started = datetime.now()
        self._timer.start()

    def stop(self):
        self._timer.cancel()

    def changeDuration(self,  duration):
        self._duration = duration

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
            pour gérer les exceptions des températures."""
        cir=""
        if ordre == "" : ordre = self.ordC
        if self.cmd in [cmdsDaikin [2], cmdsDaikin [5], cmdsDaikin [7], cmdsDaikin [10], cmdsDaikin [11], cmdsDaikin [12], cmdsDaikin [13]]:
            if ordre == "0" : ordre ='Off'
            elif ordre == "1" : ordre = 'On'
        if self.cmd == cmdsDaikin [0] :             # c'est une commande inconnue
                cir = self.ordres[""]
        elif self.cmd == cmdsDaikin [4] or self.cmd == cmdsDaikin [8] or self.cmd == cmdsDaikin [9]:   # c'est une température, l'heure de départ, l'heure de fin.
                cir=bin(opt)[2:]
                print(cir, type(cir))
                # codage binaire de opt
                if len(cir) < self.dim :    # La température ou en minutes depuis l'heure courant entre 0 et 1440 mns (24h00)
                    while int((self.dim)) - len(cir) > 0 :
                           cir ='0' + cir
                cir = cir[::-1]                # Reverse pour codage DAIKIN
                print(cir,  type(cir))
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
        print (u"*** Update current cmd {0}: {1}, option {2}".format(self.cmd, ord, opt))
        self.ordC = ord
        self.opt = opt
        return self.getIRCode(ord, self.opt)

    def extractOrdFromBinCode(self, code):
        """Décode l'ordre depuis un code 'binaire sans codeConst'"""
        try :
            val = code[self.offset:self.posFin()]
            for ord in self.ordres :
                if ord == "Bin2Num":
                    print(u" Decode cmd {0} from val : {1}".format(self.cmd, val))
                    val = "0b" + val[::-1]
                    print(val, type(val))
                    val = int(val, 2)
                    print(val)
                    return val
                elif val == self.ordres[ord] :
                    return ord
        except :
            pass
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
    def __init__ (self,  log = None ):
        self.lstTimings = []   # Suite des timings
        self._log = log
    def append (self,timing):
        """Ajoute un timing à la liste"""
        self.lstTimings.append (timing)

    def litFichIRTrans (self, fichier):
        """lit les timings d'un fichier type IRTrans"""
        try:
            fich = open (fichier,'r')
        except :
            if self._log : self._log.error(u'Error on openning file : {0}'.format(fichier))
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
    def __init__ (self, remote, nom ='test', timing = Timing()):
        self.lstCmds = []     # Suite des commandes à enchainer
        self.nom =nom        # Nom de la commande
        self.timing=timing    # timing utilisé
        self._remote = remote
        self.isUpdate = False
        self.setDatetime(datetime.now())
        self.timers = {}

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

    def append(self, cmd):     # Ajout d'une commande avec ses paramètres
        """Ajoute une commande à la collection"""
        self.lstCmds.append(cmd)

    def buildBinCodeIR(self):
        """Génère le code IR complet en fonction des valeurs courantes d'ordre, retourne une string de code binaire."""
        modExcept = {"Fan only" : 25,  "Dry" : 96}  # Valeurs corrigées en cas d'exception
        code=""
        for cmd in self.lstCmds :
            ord =""
            opt = cmd.opt
            if cmd.cmd == cmdsDaikin[4] :               # Exception pour les modes Ventillation et Condensation, la température doit-être imposée.
                mode = self.lstCmds[self.indexCmd(cmdsDaikin[3])].ordC              # récupération du mode de chauffage
                if mode in modExcept.keys():                                                    # si dans un mode d'exception -> forcer température
                    ord = "Bin2Num"
                    opt = modExcept[mode]
            code = code + cmd.getIRCode (ord, opt)
#            print(cmd.cmd, cmd.ordC, "forced : ", ord, opt)
#            print("{0}".format(code))
        code = self.cheksum(codeConst + code)
        return code

    def buildRawCodeIR(self):
        """Génère le code IR complet en fonction des valeurs courantes d'ordre,
            retourne dict avec un tableau de code RAW avec les paires pulse/pause."""
        codeB = self.buildBinCodeIR()
        codeR ={'FREQ': self.timing.freq,  'PAIRS' : []}
        for t in codeB : codeR['PAIRS'].append(self.timing.timings[int(t)])
        return codeR

    def indexCmd(self,  cmd):
        """Retourne l'index, dans la liste de commande, d'une commande particulière"""
        for id in range(0,len(self.lstCmds )):
            if self.lstCmds[id].cmd == cmd :
                return id
                break
        return -1

    def setCmd(self, cmd, value):
        """Configure une commande de la liste"""
        id = self.indexCmd(cmd)
        if id != -1 :
            if cmd in [cmdsDaikin[4], cmdsDaikin [8] , cmdsDaikin [9]]:
                ordre = "Bin2Num"
                opt = value
                if cmd in [cmdsDaikin [8] , cmdsDaikin [9]] :
                    self.handleTimer(cmd, opt)
            else :
                ordre = value
                opt = 0
            self.lstCmds[id].setCurrentValue(ordre, opt)
            return True
        else :
            return False

    def getCmd(self,  cmd = cmdsDaikin [0]):
        """Retourne l'etat d'une commande dous forme de dict {value, option}"""
        try :
            if cmd in [cmdsDaikin [8] , cmdsDaikin [9]] :
                opt = self.formatStrDelais(self.lstCmds[self.indexCmd(cmd)].opt)
            else : opt = self.lstCmds[self.indexCmd(cmd)].opt
            return {"value": self.lstCmds[self.indexCmd(cmd)].ordC ,  "option" : opt}
        except ValueError :
            raise DaikinCodeException(u"Unknows command {0}".format(cmd))


    def cheksum(self,  code):
        """Calcul le checksum d'un code complet avec le code constructeur inclu (codeConst) et y insert le cheksum"""
        c = self.lstCmds[self.indexCmd(cmdsDaikin [14])]     # récupération des valeurs de positions
        lgC = len(codeConst)
        posChk = c.offset + lgC
        chk = 0
        dataC = code[lgC +1 : posChk]                # extraction de la partie util au calcul du cheksum
        for i  in range (0, len(dataC), 8):             # extraction par pas de 8 bits
            chk=chk + int (dataC[i:i+8][::-1], 2)    # addition des bytes après reverse bits
        return code[0:posChk] + bin(chk)[::-1][0:c.dim] + code[posChk +c.dim:]   # reconstruction de code complet

    def labelEtatCmds(self) :
        """Retourne uniquement l'état des commandes utilisateur sous forme liste de dictionnaire"""
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

    def decodeCodeBin(self, codeC, forceUpdate = False):
        """Decode un code 'binaire' entier (avec le codeConst DAIKIN) et renvoie un dict des valeurs courantes et à mettre à jour."""
        lgC = len(codeConst)
        code = codeC[lgC:]
        cmdsState = self.labelEtatCmds()
        change ={}
        for cmd in self.lstCmds:
            state = cmd.extractOrdFromBinCode(code)
            if state != None :
                if cmdsState.has_key(cmd.cmd) :
                    if cmdsState[cmd.cmd] != state or forceUpdate:
                        change.update({cmd.cmd: state})
        return {'current': cmdsState, 'toUpdate' : change}

    def setDatetime(self, date):
        """Mémorise la delta entre les dates de la PAC et celle du PC."""
        self.deltaDate = datetime.now() - date

    def getCurrentDate(self):
        """Retourne le date courante supposée de la PAC, calcul par rapport à la dernière date connue."""
        return datetime.now() - self.deltaDate

    def getDateByOffset(self, mins):
        """Retourne la date avec l'offset en mins"""
        return self.getCurrentDate() + timedelta(minutes = mins)

    def getOffsetByDate(self, date):
        """Retourne l'offset en mins entre la date courante et une date définie."""
        return int(timedelta.total_seconds(date - self.getCurrentDate())/ 60)

    def formatStrDelais(self, mins):
        """Retourne la date sous forme 'hh:mm:ss.s' avec l'offset en mins"""
#        return str(timedelta(minutes = mins)) + ".0"
        if mins == 0 :
            return "00:00:00.0"
        else :
            return self.getDateByOffset(mins).strftime("%H:%M:%S.%f")[:10]

    def handleTimer(self, name,  duration):
        if self.timers.has_key(name) :
            if duration <= 0 :
                self.timers[name].stop()
                del self.timers[name]
                return
        elif duration > 0 :
            self.timers[name] = TimerDaikin(60.0, duration, self.updateTimer, self.finishTimer,  [name])
            self.timers[name].start()

    def updateTimer(self, tps, name):
        if tps < 0 : tps =0
        self.setCmd(name, int(tps))
        self._remote._manager.sendSensorUpdate({'name':self.formatStrDelais(int(tps))})

    def finishTimer(self, name):
        print "Timer {0} finish.".format(name)
        self._remote._manager.sendSensorUpdate({'name':self.formatStrDelais(0)})
        if name == cmdsDaikin [8]: state ='On'  # starttime
        else : state ='Off'
        self._remote._manager.sendSensorUpdate({'power': state})
        del self.timers[name]
        self.setCmd(name,  0)

if __name__ == '__main__' :
    cmds = CodeIRDaikin(None)
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
    cmds.setCmd("mode","heat")
    cmds.setCmd("power","On")
    cmds.setCmd("setpoint", 35)
    cmds.setCmd("vertical_swing", "On")
    cmds.setCmd("speedfan", "Auto")
    print cmds.buildBinCodeIR ()
    print cmds.labelEtatCmds()

    print tims.encodeTimingsIRTrans()
    print cmds.encodeCmdIRTrans()
