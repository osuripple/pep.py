import urllib.request
import json

from helpers import consoleHelper
from constants import bcolors

# API URL
URL = "http://ip.zxq.co/"


def getCountry(ip):
	"""
	Get country from IP address

	ip -- IP Address
	return -- Country code (2 letters)
	"""

	# Default value, sent if API is memeing
	country = "XX"

	try:
		# Try to get country from Pikolo Aul's Go-Sanic ip API
		result = json.loads(urllib.request.urlopen("{}/{}".format(URL, ip), timeout=3).read().decode())["country"]
		return result.upper()
	except:
		consoleHelper.printColored("[!] Error in get country", bcolors.RED)
		return "XX"


def getLocation(ip):
	"""
	Get latitude and longitude from IP address

	ip -- IP address
	return -- [latitude, longitude]
	"""

	# Default value, sent if API is memeing
	data = [0,0]

	try:
		# Try to get position from Pikolo Aul's Go-Sanic ip API
		result = json.loads(urllib.request.urlopen("{}/{}".format(URL, ip), timeout=3).read().decode())["loc"].split(",")
		return [float(result[0]), float(result[1])]
	except:
		consoleHelper.printColored("[!] Error in get position", bcolors.RED)
		return [0,0]
