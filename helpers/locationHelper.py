import urllib.request
import json
from objects import glob

from helpers import logHelper as log

def getCountry(ip):
	"""
	Get country from IP address

	ip -- IP Address
	return -- Country code (2 letters)
	"""
	try:
		# Try to get country from Pikolo Aul's Go-Sanic ip API
		result = json.loads(urllib.request.urlopen("{}/{}".format(glob.conf.config["localize"]["ipapiurl"], ip), timeout=3).read().decode())["country"]
		return result.upper()
	except:
		log.error("Error in get country")
		return "XX"

def getLocation(ip):
	"""
	Get latitude and longitude from IP address

	ip -- IP address
	return -- [latitude, longitude]
	"""
	try:
		# Try to get position from Pikolo Aul's Go-Sanic ip API
		result = json.loads(urllib.request.urlopen("{}/{}".format(glob.conf.config["localize"]["ipapiurl"], ip), timeout=3).read().decode())["loc"].split(",")
		return [float(result[0]), float(result[1])]
	except:
		log.error("Error in get position")
		return [0,0]
