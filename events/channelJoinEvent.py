"""
Event called when someone joins a channel
"""

from constants import clientPackets
from helpers import consoleHelper
from constants import bcolors
from constants import serverPackets
from objects import glob
from constants import exceptions
from helpers import logHelper as log

def handle(userToken, packetData):
	# Channel join packet
	packetData = clientPackets.channelJoin(packetData)
	joinChannel(userToken, packetData["channel"])

def joinChannel(userToken, channelName):
	'''
	Join a channel

	userToken -- user token object of user that joins the chanlle
	channelName -- name of channel
	'''
	try:
		# Get usertoken data
		username = userToken.username
		userID = userToken.userID

		# Check spectator channel
		# If it's spectator channel, skip checks and list stuff
		if channelName != "#spectator" and channelName != "#multiplayer":
			# Normal channel, do check stuff
			# Make sure the channel exists
			if channelName not in glob.channels.channels:
				raise exceptions.channelUnknownException

			# Check channel permissions
			if glob.channels.channels[channelName].publicRead == False and userToken.admin == False:
				raise exceptions.channelNoPermissionsException

			# Add our userID to users in that channel
			glob.channels.channels[channelName].userJoin(userID)

			# Add the channel to our joined channel
			userToken.joinChannel(channelName)

		# Send channel joined
		userToken.enqueue(serverPackets.channelJoinSuccess(userID, channelName))

		# Console output
		log.info("{} joined channel {}".format(username, channelName))
	except exceptions.channelNoPermissionsException:
		log.warning("{} attempted to join channel {}, but they have no read permissions".format(username, channelName))
	except exceptions.channelUnknownException:
		log.warning("{} attempted to join an unknown channel ({})".format(username, channelName))
