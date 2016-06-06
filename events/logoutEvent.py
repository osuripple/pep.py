from objects import glob
from helpers import consoleHelper
from constants import bcolors
from constants import serverPackets
import time
from helpers import logHelper as log

def handle(userToken, _):
	# get usertoken data
	userID = userToken.userID
	username = userToken.username
	requestToken = userToken.token

	# Big client meme here. If someone logs out and logs in right after,
	# the old logout packet will still be in the queue and will be sent to
	# the server, so we accept logout packets sent at least 5 seconds after login
	# if the user logs out before 5 seconds, he will be disconnected later with timeout check
	if int(time.time()-userToken.loginTime) >= 5:
		# Stop spectating if needed
		if userToken.spectating != 0:
			# The user was spectating someone
			spectatorHostToken = glob.tokens.getTokenFromUserID(userToken.spectating)
			if spectatorHostToken != None:
				# The host is still online, send removeSpectator to him
				spectatorHostToken.enqueue(serverPackets.removeSpectator(userID))

		# Part all joined channels
		for i in userToken.joinedChannels:
			glob.channels.channels[i].userPart(userID)

		# TODO: Lobby left if joined

		# Enqueue our disconnection to everyone else
		glob.tokens.enqueueAll(serverPackets.userLogout(userID))

		# Delete token
		glob.tokens.deleteToken(requestToken)

		# Console output
		log.info("{} has been disconnected.".format(username))
