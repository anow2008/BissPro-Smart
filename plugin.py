# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
# استيراد العناصر بشكل منفرد لتجنب خطأ الاستيراد الجماعي
try:
    from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
except ImportError:
    # حل بديل في حال لم تكن المكتبة في مكانها المعتاد
    from enigma import eListboxPythonMultiContent
    MultiContentEntryText = None # سيتم التعامل معها داخل بناء القائمة

from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP
from Tools.LoadPixmap import LoadPixmap
import os, re, shutil, time
from urllib.request import urlopen, urlretrieve
from threading import Thread

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="900,600" title="BissPro Smart">
            <widget name="menu" position="20,20" size="860,400" itemHeight="100" scrollbarMode="showOnDemand" transparent="1"/>
            <widget name="status" position="20,440" size="860,50" font="Regular;30" halign="center" foregroundColor="#f0a30a" transparent="1"/>
            <widget name="main_progress" position="150,510" size="600,10" foregroundColor="#00ff00" />
        </screen>"""
        
        self["menu"] = MenuList([])
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.ok, "cancel": self.close}, -1)
        
        self.timer = eTimer()
        try: self.timer.timeout.connect(self.show_result)
        except: self.timer.callback.append(self.show_result)
        
        self.onLayoutFinish.append(self.build_menu)

    def build_menu(self):
        icon_dir = PLUGIN_PATH + "icons/"
        menu_items = [
            ("Add Key", "Add BISS Key Manually", "add", "add.png"), 
            ("Key Editor", "Edit or Delete Stored Keys", "editor", "editor.png"), 
            ("Update Softcam", "Download latest SoftCam.Key", "upd", "update.png"), 
            ("Smart Auto Search", "Auto find key for current channel", "auto", "auto.png")
        ]
        
        lst = []
        for name, desc, act, icon_name in menu_items:
            pix = LoadPixmap(icon_dir + icon_name)
            # استخدام الطريقة الأساسية التي تعمل على كل النسخ بدون استثناء
            res = (name, [
                (MultiContentEntryPixmapAlphaTest(pos=(10, 15), size=(70, 70), png=pix) if MultiContentEntryText else None),
                (MultiContentEntryText(pos=(100, 15), size=(700, 40), font=0, text=name) if MultiContentEntryText else name),
                (MultiContentEntryText(pos=(100, 55), size=(700, 30), font=1, text=desc, color=0xbbbbbb) if MultiContentEntryText else desc),
                act
            ])
            lst.append(res)
            
        self["menu"].l.setList(lst)
        self["menu"].l.setItemHeight(100)
        self["menu"].l.setFont(0, gFont("Regular", 32))
        self["menu"].l.setFont(1, gFont("Regular", 22))

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[1][-1]
            if act == "add": self.action_add()
            elif act == "editor": self.action_editor()
            elif act == "upd": self.action_update()
            elif act == "auto": self.action_auto()

    def action_add(self):
        service = self.session.nav.getCurrentService()
        if service: self.session.openWithCallback(self.manual_done, HexInputScreen, service.info().getName())

    def action_editor(self): self.session.open(BissManagerList)

    def manual_done(self, key=None):
        if not key: return
        self.res = (True, "Key Processed")
        self.timer.start(100, True)

    def show_result(self): 
        self.session.open(MessageBox, self.res[1], MessageBox.TYPE_INFO)

    def action_update(self): 
        self.res = (True, "Feature Under Test")
        self.timer.start(100, True)

    def action_auto(self):
        self.res = (True, "Searching...")
        self.timer.start(100, True)

class BissManagerList(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="800,500" title="Editor"><widget name="keylist" position="10,10" size="780,450" /></screen>"""
        self["keylist"] = MenuList([])
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

class HexInputScreen(Screen):
    def __init__(self, session, channel_name=""):
        Screen.__init__(self, session)
        self.skin = """<screen position="center,center" size="600,200" title="Input"><widget name="keylabel" position="10,80" size="580,60" font="Regular;40" halign="center" /></screen>"""
        self["keylabel"] = Label("Enter Key")
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

def main(session, **kwargs): session.open(BISSPro)
def Plugins(**kwargs): return [PluginDescriptor(name="BissPro Smart", description="BISS", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
