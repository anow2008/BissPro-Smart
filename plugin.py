# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import iServiceInformation, gFont, eTimer, getDesktop, RT_VALIGN_TOP, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS   # <<< التعديل (import)
import os, re, shutil, time
from urllib.request import urlopen, urlretrieve
from threading import Thread

# ==========================================================
# التعريفات والروابط
# ==========================================================
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/BissPro/"
VERSION_NUM = "v1.0"
URL_VERSION = "https://raw.githubusercontent.com/anow2008/BissPro/refs/heads/main/version.txt"
URL_PLUGIN = "https://raw.githubusercontent.com/anow2008/BissPro/refs/heads/main/plugin.py"

def get_softcam_path():
    paths = ["/etc/tuxbox/config/oscam/SoftCam.Key", "/etc/tuxbox/config/ncam/SoftCam.Key",
             "/etc/tuxbox/config/SoftCam.Key", "/usr/keys/SoftCam.Key"]
    for p in paths:
        if os.path.exists(p): return p
    return "/etc/tuxbox/config/oscam/SoftCam.Key"

def restart_softcam_global():
    os.system("killall -9 oscam ncam vicardd gbox 2>/dev/null")
    time.sleep(1.2)
    scripts = ["/etc/init.d/softcam", "/etc/init.d/cardserver",
               "/etc/init.d/softcam.oscam", "/etc/init.d/softcam.ncam"]
    for s in scripts:
        if os.path.exists(s):
            os.system(f"'{s}' restart >/dev/null 2>&1")
            break

class AutoScale:
    def __init__(self):
        d = getDesktop(0).size()
        self.scale = min(d.width() / 1920.0, d.height() / 1080.0)
    def px(self, v): return int(v * self.scale)
    def font(self, v): return int(max(20, v * self.scale))

# ==========================================================
# الشاشة الرئيسية
# ==========================================================
class BISSPro(Screen):
    def __init__(self, session):
        self.ui = AutoScale()
        Screen.__init__(self, session)
        self.skin = f"""<screen position="center,center" size="{self.ui.px(1100)},{self.ui.px(780)}" title="BissPro Smart">
            <widget name="date_label" position="{self.ui.px(50)},{self.ui.px(20)}" size="{self.ui.px(450)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" transparent="1"/>
            <widget name="time_label" position="{self.ui.px(750)},{self.ui.px(20)}" size="{self.ui.px(300)},{self.ui.px(40)}" font="Regular;{self.ui.font(26)}" halign="right" transparent="1"/>
            <widget name="menu" position="{self.ui.px(50)},{self.ui.px(80)}" size="{self.ui.px(1000)},{self.ui.px(410)}" itemHeight="{self.ui.px(100)}"/>
            <widget name="status" position="{self.ui.px(50)},{self.ui.px(660)}" size="{self.ui.px(1000)},{self.ui.px(70)}" font="Regular;{self.ui.font(32)}" halign="center"/>
        </screen>"""

        self["menu"] = MenuList([])
        self["status"] = Label("Ready")

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {"ok": self.ok, "cancel": self.close},
            -1
        )
        self.onLayoutFinish.append(self.build_menu)

    def build_menu(self):
        menu_items = [
            ("Add", "Add BISS Key Manually", "add", "add.png"),
            ("Key Editor", "Edit or Delete Stored Keys", "editor", "editor.png"),
            ("Update Softcam", "Download latest SoftCam.Key", "upd", "update.png"),
            ("Smart Auto Search", "Auto find key for current channel", "auto", "auto.png")
        ]

        lst = []
        for name, desc, act, icon_name in menu_items:
            # ===== التعديل الوحيد =====
            icon_path = resolveFilename(
                SCOPE_PLUGINS,
                "Extensions/BissPro/icons/%s" % icon_name
            )
            pixmap = LoadPixmap(path=icon_path)
            # ========================

            res = (
                name,
                [
                    MultiContentEntryPixmapAlphaTest(
                        pos=(self.ui.px(15), self.ui.px(15)),
                        size=(self.ui.px(70), self.ui.px(70)),
                        png=pixmap
                    ),
                    MultiContentEntryText(
                        pos=(self.ui.px(110), self.ui.px(10)),
                        size=(self.ui.px(850), self.ui.px(45)),
                        font=0,
                        text=name,
                        flags=RT_VALIGN_TOP
                    ),
                    MultiContentEntryText(
                        pos=(self.ui.px(110), self.ui.px(55)),
                        size=(self.ui.px(850), self.ui.px(35)),
                        font=1,
                        text=desc,
                        flags=RT_VALIGN_TOP,
                        color=0xbbbbbb
                    ),
                    act
                ]
            )
            lst.append(res)

        self["menu"].l.setList(lst)
        if hasattr(self["menu"].l, "setFont"):
            self["menu"].l.setFont(0, gFont("Regular", self.ui.font(36)))
            self["menu"].l.setFont(1, gFont("Regular", self.ui.font(24)))

    def ok(self):
        self.close()

def main(session, **kwargs):
    session.open(BISSPro)

def Plugins(**kwargs):
    return [PluginDescriptor(
        name="BissPro Smart",
        description="Smart BISS Manager",
        icon="plugin.png",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main
    )]
