# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer, iServiceInformation, gFont, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
import os

# المكتبة المسؤولة عن الرسم في القوائم بطريقة Python 3
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="900,600" title="BissPro Smart v1.0">
            <widget name="menu" position="20,20" size="860,450" itemHeight="100" scrollbarMode="showOnDemand" transparent="1" />
            <widget name="status" position="20,480" size="860,40" font="Regular;30" halign="center" foregroundColor="#f0a30a" />
            <widget name="main_progress" position="150,530" size="600,10" foregroundColor="#00ff00" />
        </screen>"""
        
        self["status"] = Label("Ready")
        self["main_progress"] = ProgressBar()
        self["menu"] = MenuList([])
        
        self["actions"] = ActionMap(["OkCancelActions"], {
            "ok": self.ok,
            "cancel": self.close
        }, -1)
        
        self.onLayoutFinish.append(self.build_menu)

    def build_menu(self):
        icon_dir = PLUGIN_PATH + "icons/"
        # مصفوفة البيانات: (الاسم، الوصف، الأيقونة، الأكشن)
        options = [
            ("Add BISS Key", "Add new key manually", "add.png", "add"),
            ("Key Editor", "Manage your saved keys", "editor.png", "editor"),
            ("Update Online", "Download latest softcam file", "update.png", "upd"),
            ("Auto Search", "Find key for current channel", "auto.png", "auto")
        ]
        
        menu_list = []
        for name, desc, img, act in options:
            pix = LoadPixmap(cached=True, path=icon_dir + img)
            # بناء السطر يدوياً لضمان التوافق مع Python 3.12
            res = [
                act, # القيمة التي تعود عند الضغط
                MultiContentEntryPixmapAlphaTest(pos=(15, 15), size=(70, 70), png=pix),
                MultiContentEntryText(pos=(100, 10), size=(700, 45), font=0, text=name, flags=RT_VALIGN_CENTER),
                MultiContentEntryText(pos=(100, 55), size=(700, 35), font=1, text=desc, color=0xbbbbbb, flags=RT_VALIGN_CENTER)
            ]
            menu_list.append(res)
            
        self["menu"].l.setList(menu_list)
        self["menu"].l.setItemHeight(100)
        self["menu"].l.setFont(0, gFont("Regular", 32))
        self["menu"].l.setFont(1, gFont("Regular", 22))

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[0] # جلب الأكشن من أول عنصر في القائمة
            if act == "add": self.session.open(MessageBox, "Add Manual", MessageBox.TYPE_INFO)
            elif act == "editor": self.session.open(MessageBox, "Editor Open", MessageBox.TYPE_INFO)
            elif act == "upd": self.session.open(MessageBox, "Update Start", MessageBox.TYPE_INFO)
            elif act == "auto": self.session.open(MessageBox, "Searching...", MessageBox.TYPE_INFO)

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
