# !/usr/bin/python
#-*- coding: utf-8 -*-

#!/usr/bin/python
# -*- coding: utf-8 -*-

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
cmdsDaikin = ['Inconnue','Pulse de start','ON/OFF','Mode Fonctionnement','Température','Ventilation battante verticale','Vitesse de ventilation','Ventilation battante horizontale',
'Heure départ','Heure de fin','Mode powerful','Mode silencieux','Home leave','Sensor','Code de vérification']


class CmdDaikin:
        "Définition d'une commande type daikin"
        def __init__(self, cmd, offset, dim, ordres, ordDef, opt =0):
                "Déclaration d'une commande"
                self.cmd = cmd                     # nom de la commande
                self.offset = offset                # offset dans le code complet
                self.dim = dim                       # longueur de bit de codage
                self.ordres = ordres                # Liste des ordres et les correspondance en codage
                self.ordC = ordDef                  # Ordres par défaut
                self.opt = opt
    
        def posFin (self):
                "Renvoi la position de fin "
                return self.offset + self.dim
    
        def renvoiCodeIR (self, ordre = "", opt = 0):
                "Renvoi le code IR en fonction de la commande et de l'ordre \
           Doit-être appelé par la méthode de la class CodeIRDaikin.genererCodeIR() \
           pour géré les exceptions des températures."
                cir=""
                if ordre == "" :
                        ordre = self.ordC
                        opt =self.opt
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
                "Retroune l'état de la commande utilisateur sous forme de dictionnaire \
           Doit-être appelé par la méthode de la class CodeIRDaikin.LabelEtatCmds() \
           pour géré les exceptions des températures."
                eC ={}
                if self.cmd == cmdsDaikin [0] : eC= {}                                     # c'est une commande inconnue
                elif self.cmd == cmdsDaikin [1] : eC= {}                                  # c'est le pulse start
                elif self.cmd == cmdsDaikin [4]  :                                             # c'est la température
                    if opt == -1 : eC = {self.cmd: self.opt + "°C)"}                   # La température
                    else : eC = {self.cmd: "%d°C" % opt }                                     # Exception : La température forcée en option
                elif self.cmd == cmdsDaikin [8] or self.cmd == cmdsDaikin [9] :   # c'est l'heure de départ ou l'heure de fin.
                    eC = {self.cmd: "%d min(s)" % self.opt }                          # en minutes depuis l'heure courant entre 0 et 1440 mns (24h00)
                elif self.cmd == cmdsDaikin [14] : eC= {}                                  # c'est le cheksum
                else : eC = {self.cmd: self.ordC}            # Toute autre commande utilisateur codée dans le dictionnaire.
                return eC
            
        def ordCourant (self, ord, opt = 0):
                "Définis l'ordre et l'option courant puis renvoi le code IR"
                self.ordC = ord
                self.opt = opt
                return self.renvoiCodeIR (ord, self.opt)

class Timing:
        "Timing, pulse et pause"
        def __init__ (self, li="" ):
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
                 
        def decodeTimingITRrans (self, li):
                "Décode les informations de timing type IRTrans, issues d'un fichier IRTrans. \
                 Ligne entière du fichier"
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
            "Encode les information de timing sous format IRTrans, pour inclure dans un fichier."
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

        def affiche (self):
            "Affiche les valeurs de paramètres du timing"
            print "Numéro du timing :", self.num       
            print "     nombre de valeurs de time du timing : ", self.nbt 
            print "     listes des timings pair pulse/pause en micro sec. :", self.timings
            print "     Nombre de répétition : ", self.rc
            print "     pause entre de répétition en ms : ", self.rp
            print "     longueur de cadre du signal IR (remplace rp) : ", self.fl
            print "     fréquence du signal (0 + pas de modulation) : ", self.freq
            print "     code du bit de start (startbit) : ", self.sb
            print "     le startbit est répété : ", self.rs
            print "     RC5 code (pas besoin de timing) : ", self.rc5
            print "     RC6 code (pas besoin de timing) : ", self.rc6
            print "     RC5 / RC6 toggle bit non utilisé : ", self.notog
            

class Timings :
        "Liste des timings (pulses et pauses)"
        def __init__ (self ):
            self.lstTimings = []   # Suite des timings

        def append (self,timing):
                "Ajoute un timing à la liste"
                self.lstTimings.append (timing)

        def litFichIRTrans (self, fichier):
                "lit les timings d'un fichier type IRTrans"
                try:
                    fich = open (fichier,'r')
                except :
                    print fichier
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
                "Encode les timings pour fichier IRTRans"
                code =''
                for t in self.lstTimings:
                    code = code + t.encodeTimingIRTrans()
                return code

            
class CodeIRDaikin :
        "Liste de cmd daikin pour gestion du code complet "
        def __init__ (self,  nom ='test',  timing = 0 ):
                self.lstCmds = []     # Suite des commandes à enchainer
                self.nom =nom        # Nom de la commande
                self.timing=timing    # timing utilisé
                self.lstCmds.append (CmdDaikin (cmdsDaikin [1], 0, 1, {"0" : "2","1" : "5"}, "0"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 1, 40, {"" : "1000100001011011111001000000000000000000"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [2], 41, 1, {"OFF" : "0","ON" : "1"}, "OFF"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 42, 3, {"" : "000"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [3], 45, 3, {"Automatique" : "000",\
                                                                                            "Chauffage" : "001",\
                                                                                            "Ventilation" : "011",\
                                                                                            "Condensation" : "010",\
                                                                                            "Froid" : "110"}, "Chauffage"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 48, 2, {"" : "00"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [4], 50, 7, {"Bin2Num" : "011010"}, "Bin2Num"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 57, 8, {"" : "00000000"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [5], 64, 4, {"Désactivée" : "0000","Activée" : "1111"},"Activée"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [6], 69, 4, {"Inconnue" : "0000",\
                                                                                            "Automatique" : "0101",\
                                                                                            "Minimale" : "1101",\
                                                                                            "Vitesse 1" : "1100",\
                                                                                            "Vitesse 2" : "0010",\
                                                                                            "Vitesse 3" : "1010",\
                                                                                            "Vitesse 4" : "0110",\
                                                                                            "Vitesse 5" : "1110"}, "Automatique"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [7], 73, 4, {"Désactivée" : "0000","Activée" : "1111"}, "Désactivée"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 77, 4, {"" : "0000"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [8], 80, 12, {"Bin2Num" : "000000000000"}, "Bin2Num"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [9], 93, 12, {"Bin2Num" : "000000000000"}, "Bin2Num"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [10], 105, 1, {"Désactivée" : "0","Activée" : "1"}, "Désactivée"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 106, 4, {"" : "0000"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [11], 110, 1, {"Désactivée" : "0","Activée" : "1"}, "Désactivée"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 111, 1, {"" : "0"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [12], 112, 1, {"Désactivée" : "0","Activée" : "1"}, "Désactivée"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 113, 17, {"" : "00000000000000110"},  ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [13], 130, 1, {"Désactivée" : "0","Activée" : "1"}, "Désactivée"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 131, 14, {"" : "00000000000000"}, ""))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [14], 145, 8, {"Cheksum" : "00000000"}, "Cheksum"))
                self.lstCmds.append (CmdDaikin (cmdsDaikin [0], 153, 1, {"" : "0"}, ""))
           
        def append (self, cmd):     # Ajout d'une commande avec ses paramètres
                "Ajoute une commande à la collection"
                self.lstCmds.append (cmd)
                
        def genererCodeIR (self): 
                "Génère le code IR complet en fonction des valeurs courantes d'ordre"
                modExcept = {"Ventilation" : 25,  "Condensation" : 96}  # Valeurs corrigées en cas d'exception
                code=""
                for cmd in self.lstCmds :
                    ord =""
                    opt =0
                    if cmd.cmd == cmdsDaikin[4] :               # Exception pour les modes Ventillation et Condensation, la température doit-être imposée.
                        mode = self.lstCmds[self.indexCmd(cmdsDaikin[3])].ordC              # récupération du mode de chauffage
                        if mode in modExcept.keys():                                                    # si dans un mode d'exception -> forcer température
                            ord = "Bin2Num"
                            opt = modExcept[mode]
                    code = code + cmd.renvoiCodeIR (ord,  opt)
                code = self.cheksum(codeConst + code)
                return code
                
        def indexCmd (self,  cmd):
                "Retourne l'index, dans la liste de commande, d'une commande particulière"
                for id in range(0,len(self.lstCmds )):
                    if self.lstCmds[id].cmd == cmd :
                        return id
                        break
                return -1
                        
        def setCmd (self,  cmd = cmdsDaikin [0],  ordre = "" ,  opt = 0):  
                "Configure une commande de la liste"
                try :
                    self.lstCmds[self.indexCmd(cmd)].ordCourant(ordre, opt)
                    return 0       
                except ValueError :
                    return 1
  
        def cheksum (self,  code):
                "Calcul le checksum d'un code complet avec le code constructeurinclue (codeConst) et y insert le cheksum"
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
                "Retroune l'état des commandes utilisateur sous forme liste de dictionnaire"
                modExcept = {"Ventilation" : 25,  "Condensation" : 96}   # Valeurs corrigées en cas d'exception
                etatC =[]
                for cmd in self.lstCmds:
                    opt = -1
                    if cmd.cmd == cmdsDaikin[4] :               # Exception pour les modes Ventillation et Condensation, la température doit-être imposée.
                        mode = self.lstCmds[self.indexCmd(cmdsDaikin[3])].ordC                # récupération du mode de chauffage
                        if mode in modExcept.keys():                                                    # si dans un mode d'exception -> forcer température
                            opt = modExcept[mode]
                    lab = cmd.LabelEtatCmd(opt)
                    if lab !={} : etatC.append(lab)
                return etatC
                
        def encodeCmdIRTrans(self):
                "Encode en ligne ASCII la commande pour format fichier IRTrans"
                return  '  [%s][T]%d[D]%s' %(self.nom,  self.timing,  self.genererCodeIR ())
                
                
                
                


if __name__ == '__main__' :
    cmds = CodeIRDaikin()
    a, nb = 0, 23
    while a < nb :
        print cmds.lstCmds[a].cmd, " --> ", cmds.lstCmds[a].ordC
        a=a+1
    print cmds.genererCodeIR ()                 
    tims = Timings()
    tims.litFichIRTrans("Daikin.rem")
   
    print ' '

    cmds.setCmd("Mode Fonctionnement","Ventilation")
    cmds.setCmd("ON/OFF","ON")
    cmds.setCmd("Température", opt = 35)  
    cmds.setCmd("Ventilation battante verticale", "Activée")
    cmds.setCmd("Vitesse de ventilation", "Automatique")
    print cmds.genererCodeIR ()
    for lab in cmds.labelEtatCmds() :
        print lab.keys(),  lab.values()

    print tims.encodeTimingsIRTrans()
    print cmds.encodeCmdIRTrans()
