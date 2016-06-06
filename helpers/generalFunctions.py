"""Some functions that don't fit in any other file"""
from constants import mods
from time import gmtime, strftime

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

	return ":".join("{:02x}".format(ord(c)) for c in s)

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
	hdfl = (__mods & mods.Hidden > 0) or (__mods & mods.Flashlight > 0)

	def ss():
		return "sshd" if hdfl else "ss"

	def s():
		return "shd" if hdfl else "s"

	if gameMode == 0:
		# osu!std
		if acc == 100:
			return ss()
		if c300 / total > 0.90 and c50 / total < 0.1 and cmiss == 0:
			return s()
		if (c300 / total > 0.80 and cmiss == 0) or (c300 / total > 0.90):
			return "a"
		if (c300 / total > 0.70 and cmiss == 0) or (c300 / total > 0.80):
			return "b"
		if c300 / total > 0.60:
			return "c"
		return "d"
	elif gameMode == 1:
		# taiko not implemented as of yet.
		return "a"
	elif gameMode == 2:
		# CtB
		if acc == 100:
			return ss()
		if acc >= 98.01 and acc <= 99.99:
			return s()
		if acc >= 94.01 and acc <= 98.00:
			return "a"
		if acc >= 90.01 and acc <= 94.00:
			return "b"
		if acc >= 98.01 and acc <= 90.00:
			return "c"
		return "d"
	elif gameMode == 3:
		# osu!mania
		if acc == 100:
			return ss()
		if acc > 95:
			return s()
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
