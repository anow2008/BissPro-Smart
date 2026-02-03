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

# تأكد أن هذا المسار هو المجلد الذي يحتوي على مجلد icons
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"

class BISSPro(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = """
        <screen position="center,center" size="900,500" title="BissPro Smart v1.0">
            <widget name="icon" position="40,80" size="128,128" alphatest="blend" />
            <widget name="menu" position="200,60" size="650,300" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="60" />
            <widget name="status" position="20,400" size="860,40" font="Regular;28" halign="center" foregroundColor="#f0a30a" />
            <eLabel text="Use OK to select your option" position="20,450" size="860,30" font="Regular;20" halign="center" foregroundColor="#bbbbbb" />
        </screen>"""
        
        self["icon"] = Pixmap()
        self["status"] = Label("Ready")
        
        self.options = [
            ("Add BISS Key Manually", "add", "add.png"),
            ("BISS Key Editor", "editor", "editor.png"),
            ("Update Softcam Online", "upd", "update.png"),
            ("Smart Auto Search", "auto", "auto.png")
        ]
        
        # ملء القائمة بالأسماء فقط
        self["menu"] = MenuList([x[0] for x in self.options])
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "up": self.change_selection,
            "down": self.change_selection
        }, -1)
        
        self.onLayoutFinish.append(self.change_selection)

    def change_selection(self):
        # تنفيذ تغيير الأيقونة
        try:
            idx = self["menu"].getSelectedIndex()
            if idx is not None:
                icon_name = self.options[idx][2]
                icon_path = os.path.join(PLUGIN_PATH, "icons", icon_name)
                
                if os.path.exists(icon_path):
                    self["icon"].instance.setPixmap(LoadPixmap(path=icon_path))
                else:
                    # إذا لم يجد الأيقونة يضع لوجو البلجن الافتراضي
                    default_path = os.path.join(PLUGIN_PATH, "plugin.png")
                    if os.path.exists(default_path):
                        self["icon"].instance.setPixmap(LoadPixmap(path=default_path))
        except Exception as e:
            print("[BissPro] Error loading icon:", str(e))

    def ok(self):
        idx = self["menu"].getSelectedIndex()
        if idx is not None:
            act = self.options[idx][1]
            # هنا سنضع الوظائف الحقيقية لاحقاً
            self.session.open(MessageBox, "Executing: " + self.options[idx][0], MessageBox.TYPE_INFO)

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(name="BissPro Smart", description="BISS Manager", icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
