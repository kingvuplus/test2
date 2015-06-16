from config import config, ConfigSlider, ConfigSelection, ConfigYesNo, \
	ConfigEnableDisable, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave
from enigma import eAVSwitch, getDesktop
from SystemInfo import SystemInfo
from os import path as os_path, access, W_OK

class AVSwitch:
	def setInput(self, input):
		INPUT = { "ENCODER": 0, "SCART": 1, "AUX": 2 }
		eAVSwitch.getInstance().setInput(INPUT[input])

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)

	def setAspectRatio(self, value):
		eAVSwitch.getInstance().setAspectRatio(value)

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)

	def getOutputAspect(self):
		valstr = config.av.aspectratio.value
		if valstr in ("4_3_letterbox", "4_3_panscan"): # 4:3
			return (4,3)
		elif valstr == "16_9": # auto ... 4:3 or 16:9
			try:
				aspect_str = open("/proc/stb/vmpeg/0/aspect", "r").read()
				if aspect_str == "1": # 4:3
					return (4,3)
			except IOError:
				pass
		elif valstr in ("16_9_always", "16_9_letterbox"): # 16:9
			pass
		elif valstr in ("16_10_letterbox", "16_10_panscan"): # 16:10
			return (16,10)
		return (16,9)

	def getFramebufferScale(self):
		aspect = self.getOutputAspect()
		fb_size = getDesktop(0).size()
		return (aspect[0] * fb_size.height(), aspect[1] * fb_size.width())

	def getAspectRatioSetting(self):
		valstr = config.av.aspectratio.value
		if valstr == "4_3_letterbox":
			val = 0
		elif valstr == "4_3_panscan":
			val = 1
		elif valstr == "16_9":
			val = 2
		elif valstr == "16_9_always":
			val = 3
		elif valstr == "16_10_letterbox":
			val = 4
		elif valstr == "16_10_panscan":
			val = 5
		elif valstr == "16_9_letterbox":
			val = 6
		return val

	def setAspectWSS(self, aspect=None):
		if not config.av.wss.value:
			value = 2 # auto(4:3_off)
		else:
			value = 1 # auto
		eAVSwitch.getInstance().setWSS(value)

def InitAVSwitch():
	config.av = ConfigSubsection()
	config.av.yuvenabled = ConfigBoolean(default=False)
	colorformat_choices = {"cvbs": _("CVBS"), "rgb": _("RGB"), "svideo": _("S-Video")}
	
	# when YUV is not enabled, don't let the user select it
	if config.av.yuvenabled.value:
		colorformat_choices["yuv"] = _("YPbPr")

	config.av.colorformat = ConfigSelection(choices=colorformat_choices, default="cvbs")
	config.av.aspectratio = ConfigSelection(choices={
			"4_3_letterbox": _("4:3 Letterbox"),
			"4_3_panscan": _("4:3 PanScan"), 
			"16_9": _("16:9"), 
			"16_9_always": _("16:9 always"),
			"16_10_letterbox": _("16:10 Letterbox"),
			"16_10_panscan": _("16:10 PanScan"), 
			"16_9_letterbox": _("16:9 Letterbox")}, 
			default = "4_3_letterbox")

	config.av.aspect = ConfigSelection(choices={
			"4_3": _("4:3"),
			"16_9": _("16:9"), 
			"16_10": _("16:10"),
			"auto": _("Automatic")},
			default = "auto")
	config.av.policy_169 = ConfigSelection(choices={
				# TRANSLATORS: (aspect ratio policy: black bars on top/bottom) in doubt, keep english term.
			"letterbox": _("Letterbox"), 
				# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
			"panscan": _("Pan&Scan"),  
				# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if this breaks the aspect)
			"scale": _("Just Scale")},
			default = "letterbox")
	config.av.policy_43 = ConfigSelection(choices={
				# TRANSLATORS: (aspect ratio policy: black bars on left/right) in doubt, keep english term.
			"pillarbox": _("Pillarbox"), 
				# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
			"panscan": _("Pan&Scan"),  
				# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the left/right)
			"nonlinear": _("Nonlinear"),  
				# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if this breaks the aspect)
			"scale": _("Just Scale")},
			default = "pillarbox")
	config.av.tvsystem = ConfigSelection(choices = {"pal": _("PAL"), "ntsc": _("NTSC"), "multinorm": _("multinorm")}, default="pal")
	config.av.wss = ConfigEnableDisable(default = True)
	config.av.defaultac3 = ConfigYesNo(default = False)
	config.av.generalAC3delay = ConfigSelectionNumber(-1000, 1000, 25, default = 0)
	config.av.generalPCMdelay = ConfigSelectionNumber(-1000, 1000, 25, default = 0)
	config.av.vcrswitch = ConfigEnableDisable(default = False)

	iAVSwitch = AVSwitch()

	def setColorFormat(configElement):
		map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		iAVSwitch.setColorFormat(map[configElement.value])

	def setAspectRatio(configElement):
		map = {"4_3_letterbox": 0, "4_3_panscan": 1, "16_9": 2, "16_9_always": 3, "16_10_letterbox": 4, "16_10_panscan": 5, "16_9_letterbox" : 6}
		iAVSwitch.setAspectRatio(map[configElement.value])

	def setSystem(configElement):
		map = {"pal": 0, "ntsc": 1, "multinorm" : 2}
		iAVSwitch.setSystem(map[configElement.value])

	def setWSS(configElement):
		iAVSwitch.setAspectWSS()

	# this will call the "setup-val" initial
	config.av.colorformat.addNotifier(setColorFormat)
	config.av.aspectratio.addNotifier(setAspectRatio)
	config.av.tvsystem.addNotifier(setSystem)
	config.av.wss.addNotifier(setWSS)

	iAVSwitch.setInput("ENCODER") # init on startup
	SystemInfo["ScartSwitch"] = eAVSwitch.getInstance().haveScartSwitch()

	config.av.bypass_edid_checking = ConfigSelection(choices={
			"00000000": _("off"),
			"00000001": _("on")},
			default = "00000000")
	
	def setEDIDBypass(configElement):
		f = open("/proc/stb/hdmi/bypass_edid_checking", "w")
		f.write(configElement.value)
		f.close()
		
	config.av.bypass_edid_checking.addNotifier(setEDIDBypass)

	can_pcm_multichannel = False
	if SystemInfo["CanMultiChannelPCM"]:
		config.av.multichannel_pcm = ConfigYesNo(default = False)
		can_pcm_multichannel = True
		if config.av.multichannel_pcm.value:
			try:
				can_pcm_multichannel = access("/proc/stb/audio/multichannel_pcm", W_OK) and True or False
			except:
				can_pcm_multichannel = False
	SystemInfo["supportMultiChannelPCM"] = can_pcm_multichannel

	can_speaker_position = False
	if os_path.exists("/proc/stb/audio/3d_surround_speaker_position_choices"):
		can_speaker_position = True
	SystemInfo["supportSpeakerPosition"] = can_speaker_position
	if SystemInfo["CanSpeakerPosition"]:
		choice_list = [("center", _("center")), ("wide", _("wide")), ("extrawide", _("extrawide"))]
		config.av.surround_speaker_position = ConfigSelection(choices = choice_list, default = "wide")

	if SystemInfo["Can3DSurround"]:
		def set3DSurround(configElement):
			f = open("/proc/stb/audio/3d_surround", "w")
			f.write(configElement.value)
			f.close()
			if SystemInfo["supportSpeakerPosition"] and config.av.surround_3d.value == "none":
				config.av.surround_speaker_position.value = "wide"
				config.av.surround_speaker_position.save()
				SystemInfo["CanSpeakerPosition"] = False
			elif SystemInfo["supportSpeakerPosition"] and config.av.surround_3d.value != "none":
				SystemInfo["CanSpeakerPosition"] = True
		choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
		config.av.surround_3d = ConfigSelection(choices = choice_list, default = "none")
		config.av.surround_3d.addNotifier(set3DSurround)

	if SystemInfo["supportSpeakerPosition"]:
		def setSpeakerPosition(configElement):
			f = open("/proc/stb/audio/3d_surround_speaker_position", "w")
			f.write(configElement.value)
			f.close()
		config.av.surround_speaker_position.addNotifier(setSpeakerPosition)

	if SystemInfo["CanAVL"]:
		def setAVL(configElement):
			f = open("/proc/stb/audio/avl", "w")
			f.write(configElement.value)
			f.close()
		choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
		config.av.avl = ConfigSelection(choices = choice_list, default = "none")
		config.av.avl.addNotifier(setAVL)

	if SystemInfo["CanDownmixAC3"]:
		def setAC3Downmix(configElement):
			open("/proc/stb/audio/ac3", "w").write(configElement.value and "downmix" or "passthrough")
			if SystemInfo["supportMultiChannelPCM"] and (not config.av.downmix_ac3.value):
				SystemInfo["CanMultiChannelPCM"] = True
			elif SystemInfo["supportMultiChannelPCM"] and config.av.downmix_ac3.value:
				SystemInfo["CanMultiChannelPCM"] = False
				config.av.multichannel_pcm.value = False
				config.av.multichannel_pcm.save()
		config.av.downmix_ac3 = ConfigYesNo(default = True)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)

	if SystemInfo["CanDownmixAAC"]:
		def setAACDownmix(configElement):
			open("/proc/stb/audio/aac", "w").write(configElement.value and "downmix" or "passthrough")
		config.av.downmix_aac = ConfigYesNo(default = True)
		config.av.downmix_aac.addNotifier(setAACDownmix)

	def setMultiChannelPCM(configElement):
		open("/proc/stb/audio/multichannel_pcm", "w").write(configElement.value and "enable" or "disable")
	if SystemInfo["supportMultiChannelPCM"]:
		config.av.multichannel_pcm.addNotifier(setMultiChannelPCM, initial_call = config.av.multichannel_pcm.value)

	try:
		can_osd_alpha = open("/proc/stb/video/alpha", "r") and True or False
	except:
		can_osd_alpha = False

	SystemInfo["CanChangeOsdAlpha"] = can_osd_alpha

	def setAlpha(config):
		open("/proc/stb/video/alpha", "w").write(str(config.value))

	if can_osd_alpha:
		config.av.osd_alpha = ConfigSlider(default=255, limits=(0,255))
		config.av.osd_alpha.addNotifier(setAlpha)

	if os_path.exists("/proc/stb/vmpeg/0/pep_scaler_sharpness"):
		def setScaler_sharpness(config):
			myval = int(config.value)
			try:
				print "--> setting scaler_sharpness to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_scaler_sharpness", "w").write("%0.8X" % myval)
				open("/proc/stb/vmpeg/0/pep_apply", "w").write("1")
			except IOError:
				print "couldn't write pep_scaler_sharpness"

		config.av.scaler_sharpness = ConfigSlider(default=0, limits=(0,26))
		config.av.scaler_sharpness.addNotifier(setScaler_sharpness)
	else:
		config.av.scaler_sharpness = NoSave(ConfigNothing())
