"""Some functions that don't fit in any other file"""
from constants import mods

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
