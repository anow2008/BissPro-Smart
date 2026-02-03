# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import eTimer
from Tools.LoadPixmap import LoadPixmap
import os

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        # وضعنا Pixmap منفصل لعرض الأيقونة بجانب القائمة
        self.skin = """
        <screen position="center,center" size="900,500" title="BissPro Smart v1.0">
            <widget name="icon" position="40,60" size="128,128" alphatest="blend" />
            <widget name="menu" position="200,60" size="650,300" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="60" />
            <widget name="status" position="20,400" size="860,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <eLabel text="Use OK to select your option" position="20,450" size="860,30" font="Regular;20" halign="center" foregroundColor="#bbbbbb" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        self["menu"] = MenuList([])
        
        # القائمة تحتوي على الاسم، الوصف، واسم ملف الأيقونة
        self.options = [
            ("Add BISS Key Manually", "add", "add.png"),
            ("BISS Key Editor", "editor", "editor.png"),
            ("Update Softcam Online", "upd", "update.png"),
            ("Smart Auto Search", "auto", "auto.png")
        ]
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "up": self.update_icon, # تحديث الأيقونة عند الصعود
            "down": self.update_icon # تحديث الأيقونة عند النزول
        }, -1)
        
        self.onLayoutFinish.append(self.start_plugin)

    def start_plugin(self):
        # ملء القائمة بالنصوص فقط لتجنب الكراش
        self["menu"].setList([x[0] for x in self.options])
        self.update_icon()

    def update_icon(self):
        # كود تغيير الأيقونة بناءً على الخيار المختار
        idx = self["menu"].getSelectedIndex()
        if idx < len(self.options):
            icon_file = self.options[idx][2]
            full_path = PLUGIN_PATH + "icons/" + icon_file
            if os.path.exists(full_path):
                self["icon"].instance.setPixmap(LoadPixmap(path=full_path))

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        if idx < len(self.options):
            act = self.options[idx][1]
            self.session.open(MessageBox, "Option Selected: " + act, MessageBox.TYPE_INFO)

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
