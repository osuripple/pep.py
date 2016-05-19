import requests
from objects import glob
from helpers import generalFunctions
from urllib.parse import urlencode

def sendDiscordMessage(channel, message):
	"""
	Send a message to a discord server.
	This is used with ripple's schiavobot.

	channel -- bunk, staff or general
	message -- message to send
	"""
	if generalFunctions.stringToBool(glob.conf.config["discord"]["enable"]) == True:
		requests.get("{}/{}?{}".format(glob.conf.config["discord"]["boturl"], channel, urlencode({ "message": message })))


def sendConfidential(message):
	"""
	Send a message to #bunker

	message -- message to send
	"""
	sendDiscordMessage("bunk", message)


def sendChatlog(message):
	"""
	Send a message to #chatlog

	message -- message to send
	"""
	sendDiscordMessage("chatlog", message)


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
