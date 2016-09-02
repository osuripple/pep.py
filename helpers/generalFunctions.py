from constants import mods
from time import gmtime, strftime
import hashlib

def stringMd5(string):
	"""
	Return string's md5

	string -- string to hash
	return -- string's md5 hash
	"""
	d = hashlib.md5()
	d.update(string.encode("utf-8"))
	return d.hexdigest()

def stringToBool(s):
	"""
	Convert a string (True/true/1) to bool

	s -- string/int value
	return -- True/False
	"""
	return (s == "True" or s== "true" or s == "1" or s == 1)

def hexString(s):
	"""
	Output s' bytes in HEX

	s -- string
	return -- string with hex value
	"""
	return ":".join("{:02x}".format(ord(str(c))) for c in s)

def readableMods(__mods):
	"""
	Return a string with readable std mods.
	Used to convert a mods number for oppai

	__mods -- mods bitwise number
	return -- readable mods string, eg HDDT
	"""
	r = ""
	if __mods == 0:
		return r
	if __mods & mods.NoFail > 0:
		r += "NF"
	if __mods & mods.Easy > 0:
		r += "EZ"
	if __mods & mods.Hidden > 0:
		r += "HD"
	if __mods & mods.HardRock > 0:
		r += "HR"
	if __mods & mods.DoubleTime > 0:
		r += "DT"
	if __mods & mods.HalfTime > 0:
		r += "HT"
	if __mods & mods.Flashlight > 0:
		r += "FL"
	if __mods & mods.SpunOut > 0:
		r += "SO"

	return r

def getRank(gameMode, __mods, acc, c300, c100, c50, cmiss):
	"""
	Return a string with rank/grade for a given score.
	Used mainly for "tillerino"

	gameMode -- mode (0 = osu!, 1 = Taiko, 2 = CtB, 3 = osu!mania)
	__mods -- mods bitwise number
	acc -- accuracy
	c300 -- 300 hit count
	c100 -- 100 hit count
	c50 -- 50 hit count
	cmiss -- miss count
	return -- rank/grade string
	"""
	total = c300 + c100 + c50 + cmiss
	hdfl = (__mods & (mods.Hidden | mods.Flashlight | mods.FadeIn)) > 0

	ss = "sshd" if hdfl else "ss"
	s = "shd" if hdfl else "s"

	if gameMode == 0 or gameMode == 1:
		# osu!std / taiko
		ratio300 = c300 / total
		ratio50 = c50 / total
		if ratio300 == 1:
			return ss
		if ratio300 > 0.9 and ratio50 <= 0.01 and cmiss == 0:
			return s
		if (ratio300 > 0.8 and cmiss == 0) or (ratio300 > 0.9):
			return "a"
		if (ratio300 > 0.7 and cmiss == 0) or (ratio300 > 0.8):
			return "b"
		if ratio300 > 0.6:
			return "c"
		return "d"
	elif gameMode == 2:
		# CtB
		if acc == 100:
			return ss
		if acc > 98:
			return s
		if acc > 94:
			return "a"
		if acc > 90:
			return "b"
		if acc > 85:
			return "c"
		return "d"
	elif gameMode == 3:
		# osu!mania
		if acc == 100:
			return ss
		if acc > 95:
			return s
		if acc > 90:
			return "a"
		if acc > 80:
			return "b"
		if acc > 70:
			return "c"
		return "d"

	return "a"

def strContains(s, w):
	return (' ' + w + ' ') in (' ' + s + ' ')

def getTimestamp():
	"""
	Return current time in YYYY-MM-DD HH:MM:SS format.
	Used in logs.
	"""
	return strftime("%Y-%m-%d %H:%M:%S", gmtime())
