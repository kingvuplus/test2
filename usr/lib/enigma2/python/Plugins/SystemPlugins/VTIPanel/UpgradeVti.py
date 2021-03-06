# 2015.06.16 12:53:12 CET
#Embedded file name: /usr/lib/enigma2/python/Plugins/SystemPlugins/VTIPanel/UpgradeVti.py
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Ipkg import Ipkg
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap
from Components.config import config, ConfigYesNo
from Components.Ipkg import IpkgComponent
from Components.Sources.StaticText import StaticText
from Components.Slider import Slider
from Components.Console import Console
from Components.Network import iNetwork
from enigma import eTimer
from os import statvfs, remove, path as os_path
from __init__ import _
from BackupSuite import BackupActions
update_trigger = '/tmp/do_update'

class UpdatePlugin(Screen):
    skin = '\n\t\t<screen name="UpdatePlugin" position="center,center" size="550,300" title="Software update" >\n\t\t\t<widget name="activityslider" position="0,0" size="550,5"  />\n\t\t\t<widget name="slider" position="0,150" size="550,30"  />\n\t\t\t<widget source="package" render="Label" position="10,30" size="540,20" font="Regular;18" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />\n\t\t\t<widget source="status" render="Label" position="10,180" size="540,100" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />\n\t\t</screen>'

    def __init__(self, session, args = None):
        Screen.__init__(self, session)
        self.sliderPackages = {'vuplus-dvb-modules': 1,
         'enigma2': 2,
         'opera-hbbtv': 3}
        self.slider = Slider(0, 4)
        self['slider'] = self.slider
        self.activityslider = Slider(0, 100)
        self['activityslider'] = self.activityslider
        self.status = StaticText(_('Please wait...'))
        self['status'] = self.status
        self.package = StaticText(_('Verifying your internet connection...'))
        self['package'] = self.package
        self.oktext = _('Press OK on your remote control to continue.')
        self.packages = 0
        self.error = 0
        self.processed_packages = []
        self.activity = 0
        self.activityTimer = eTimer()
        self.activityTimer.callback.append(self.doActivityTimer)
        self.ipkg = IpkgComponent()
        self.ipkg.addCallback(self.ipkgCallback)
        self.updating = False
        self['actions'] = ActionMap(['WizardActions'], {'ok': self.keyOk,
         'back': self.exit}, -1)
        iNetwork.checkNetworkState(self.checkNetworkCB)
        self.onClose.append(self.cleanup)

    def startUpgrade(self):
        update_options = ' '
        if config.usage.use_force_overwrite.value:
            update_options += '--force-overwrite '
        if config.usage.use_package_conffile.value:
            update_options += '--force-maintainer '
        f = open(update_trigger, 'w+')
        f.write(update_options)
        f.close()
        config.usage.update_available.value = False
        self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

    def cleanup(self):
        iNetwork.stopPingConsole()

    def getFreeSpace(self, mountpoint):
        if mountpoint:
            stat_info = statvfs(mountpoint)
            free_flash_space = stat_info.f_bfree * stat_info.f_bsize
            return free_flash_space

    def doBackupSuite(self):
        backupactions = BackupActions('auto')
        if backupactions.createPluginList() and backupactions.createSettingFile() and backupactions.createConfigFile():
            backupactions.houseKeeping()
            return True
        backupactions.houseKeeping()
        msg = _('There was a problem at creating an automatic backup for VTi BackupSuite. Do you really want to continue ?')
        self.session.openWithCallback(self.cbBackupSuite, MessageBox, msg, MessageBox.TYPE_YESNO, default=False)

    def cbBackupSuite(self, result = None):
        if result:
            self.startUpgrade()
        else:
            self.close()

    def checkFreeSpace(self):
        free_flash_space = self.getFreeSpace('/')
        if free_flash_space > 19000000:
            if self.doBackupSuite():
                self.startUpgrade()
        else:
            human_free_space = free_flash_space / 1048576
            msg = _('There are only %d MB free FLASH space available\nInstalling or updating software can cause serious software problems !\nContinue installing/updating software (at your own risk) ?') % human_free_space
            self.session.openWithCallback(self.cbSpaceCheck, MessageBox, msg, MessageBox.TYPE_YESNO, default=False)

    def cbSpaceCheck(self, result):
        if not result:
            self.close()
        elif self.doBackupSuite():
            self.startUpgrade()

    def checkNetworkCB(self, data):
        if data is not None:
            if data <= 2:
                self.updating = True
                self.activityTimer.start(100, False)
                self.package.setText(_('Package list update'))
                self.status.setText(_('Upgrading STB... Please wait'))
                self.checkFreeSpace()
            else:
                self.package.setText(_('Your network is not working. Please try again.'))
                self.status.setText(self.oktext)

    def doActivityTimer(self):
        self.activity += 1
        if self.activity == 100:
            self.activity = 0
        self.activityslider.setValue(self.activity)

    def ipkgCallback(self, event, param):
        if event == IpkgComponent.EVENT_DOWNLOAD:
            self.status.setText(_('Downloading'))
        elif event == IpkgComponent.EVENT_UPGRADE:
            if self.sliderPackages.has_key(param):
                self.slider.setValue(self.sliderPackages[param])
            self.package.setText(param)
            self.status.setText(_('Upgrading'))
            if param not in self.processed_packages:
                self.processed_packages.append(param)
                self.packages += 1
        elif event == IpkgComponent.EVENT_INSTALL:
            self.package.setText(param)
            self.status.setText(_('Installing'))
            if param not in self.processed_packages:
                self.processed_packages.append(param)
                self.packages += 1
        elif event == IpkgComponent.EVENT_REMOVE:
            self.package.setText(param)
            self.status.setText(_('Removing'))
            if param not in self.processed_packages:
                self.processed_packages.append(param)
                self.packages += 1
        elif event == IpkgComponent.EVENT_CONFIGURING:
            self.package.setText(param)
            self.status.setText(_('Configuring'))
        elif event == IpkgComponent.EVENT_MODIFIED:
            self.ipkg.write('Y')
        elif event == IpkgComponent.EVENT_ERROR:
            self.error += 1
        elif event == IpkgComponent.EVENT_DONE:
            if self.updating:
                self.updating = False
                if config.usage.use_package_conffile.value == True:
                    upgrade_args = {'use_maintainer': True,
                     'test_only': False}
                else:
                    upgrade_args = {'use_maintainer': False,
                     'test_only': False}
                if config.usage.use_force_overwrite.value:
                    upgrade_args['force_overwrite'] = True
                else:
                    upgrade_args['force_overwrite'] = False
                self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE, args=upgrade_args)
            elif self.error == 0:
                self.slider.setValue(4)
                self.activityTimer.stop()
                self.activityslider.setValue(0)
                self.package.setText(_('Done - Installed or upgraded %d packages') % self.packages)
                self.status.setText(self.oktext)
            else:
                self.activityTimer.stop()
                self.activityslider.setValue(0)
                error = _('your STB might be unusable now. Please consult the manual for further assistance before rebooting your STB.')
                if self.packages == 0:
                    error = _('No packages were upgraded yet. So you can check your network and try again.')
                if self.updating:
                    error = _("Your STB isn't connected to the internet properly. Please check it and try again.")
                self.status.setText(_('Error') + ' - ' + error)

    def modificationCallback(self, res):
        self.ipkg.write(res and 'N' or 'Y')

    def keyOk(self):
        if not self.updating:
            self.exit()

    def exit(self):
        if not self.ipkg.isRunning():
            if self.packages == 0 and os_path.exists(update_trigger):
                remove(update_trigger)
            if self.packages != 0 and self.error == 0:
                f = open(update_trigger, 'w+').close()
                self.session.openWithCallback(self.exitAnswer, MessageBox, _('Upgrade finished.') + ' ' + _('Do you want to reboot your STB?'))
            else:
                self.close()
        else:
            self.ipkg.stop()
            self.close()

    def exitAnswer(self, result):
        if result is not None and result:
            self.session.open(TryQuitMainloop, 4)
        self.close()
