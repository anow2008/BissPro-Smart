# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer, gFont, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
import os

# استدعاء المكونات بالطريقة الصحيحة لصور OpenATV الحديثة
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="900,600" title="BissPro Smart v1.0">
            <widget name="menu" position="20,20" size="860,450" itemHeight="110" scrollbarMode="showOnDemand" transparent="1" />
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
        options = [
            ("Add BISS Key", "Add new key manually", "add.png", "add"),
            ("Key Editor", "Manage your saved keys", "editor.png", "editor"),
            ("Update Online", "Download latest softcam file", "update.png", "upd"),
            ("Auto Search", "Find key for current channel", "auto.png", "auto")
        ]
        
        menu_list = []
        for name, desc, img, act in options:
            pix = LoadPixmap(path=icon_dir + img)
            # في بايثون 3.12، يجب وضع العناصر داخل قائمة [] وتمريرها كـ Tuple
            res = (act, [
                MultiContentEntryPixmapAlphaTest(pos=(15, 20), size=(70, 70), png=pix),
                MultiContentEntryText(pos=(100, 15), size=(700, 45), font=0, text=name, flags=RT_VALIGN_CENTER),
                MultiContentEntryText(pos=(100, 60), size=(700, 35), font=1, text=desc, color=0xbbbbbb, flags=RT_VALIGN_CENTER)
            ])
            menu_list.append(res)
            
        self["menu"].l.setList(menu_list)
        self["menu"].l.setItemHeight(110)
        self["menu"].l.setFont(0, gFont("Regular", 34))
        self["menu"].l.setFont(1, gFont("Regular", 22))

    def ok(self):
        curr = self["menu"].getCurrent()
        if curr:
            act = curr[0]
            self.session.open(MessageBox, "Action: " + act, MessageBox.TYPE_INFO)

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
