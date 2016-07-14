"""
Event called when someone parts a channel
"""

from helpers import consoleHelper
from constants import bcolors
from objects import glob
from constants import clientPackets
from constants import serverPackets
from helpers import logHelper as log
from helpers import chatHelper as chat

def handle(userToken, packetData):
	# Channel join packet
	packetData = clientPackets.channelPart(packetData)
	chat.partChannel(token=userToken, channel=packetData["channel"])

"""def partChannel(userToken, channelName, kick = False):
	# Get usertoken data
	username = userToken.username
	userID = userToken.userID

	# Remove us from joined users and joined channels
	if channelName in glob.channels.channels:
		# Check that user is in channel
		if channelName in userToken.joinedChannels:
			userToken.partChannel(channelName)

		# Check if user is in channel
		if userID in glob.channels.channels[channelName].connectedUsers:
			glob.channels.channels[channelName].userPart(userID)

		# Force close tab if needed
		if kick == True:
			userToken.enqueue(serverPackets.channelKicked(channelName))

		# Console output
		log.info("{} parted channel {}".format(username, channelName))"""
