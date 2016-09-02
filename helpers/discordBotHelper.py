import requests
from objects import glob
from urllib.parse import urlencode

def sendDiscordMessage(channel, message, alertDev = False, prefix = "**pep.py**"):
	"""
	Send a message to a discord server.
	This is used with ripple's schiavobot.

	channel -- bunk, staff or general
	message -- message to send
	alertDev -- if True, hl developers group
	prefix -- string to prepend to message
	"""
	if glob.discord:
		for _ in range(0,20):
			try:
				finalMsg = "{prefix} {message}".format(prefix=prefix, message=message) if alertDev == False else "{prefix} {hl} - {message}".format(prefix=prefix, hl=glob.conf.config["discord"]["devgroup"], message=message)
				requests.get("{}/{}?{}".format(glob.conf.config["discord"]["boturl"], channel, urlencode({ "message": finalMsg })))
				break
			except:
				continue

def sendConfidential(message, alertDev = False):
	"""
	Send a message to #bunker

	message -- message to send
	"""
	sendDiscordMessage("bunk", message, alertDev)

def sendStaff(message):
	"""
	Send a message to #staff

	message -- message to send
	"""
	sendDiscordMessage("staff", message)

def sendGeneral(message):
	"""
	Send a message to #general

	message -- message to send
	"""
	sendDiscordMessage("general", message)

def sendChatlog(message):
	"""
	Send a message to #chatlog

	message -- message to send
	"""
	sendDiscordMessage("chatlog", message, prefix="")

def sendCM(message):
	"""
	Send a message to #communitymanagers

	message -- message to send
	"""
	sendDiscordMessage("cm", message)
