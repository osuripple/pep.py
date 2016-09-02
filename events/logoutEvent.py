from objects import glob
from constants import serverPackets
import time
from helpers import logHelper as log
from helpers import chatHelper as chat

def handle(userToken, _=None):
	# get usertoken data
	userID = userToken.userID
	username = userToken.username
	requestToken = userToken.token

	# Big client meme here. If someone logs out and logs in right after,
	# the old logout packet will still be in the queue and will be sent to
	# the server, so we accept logout packets sent at least 5 seconds after login
	# if the user logs out before 5 seconds, he will be disconnected later with timeout check
	if int(time.time()-userToken.loginTime) >= 5 or userToken.irc == True:
		# Stop spectating
		userToken.stopSpectating()

		# Part matches
		userToken.partMatch()
		
		# Part all joined channels
		for i in userToken.joinedChannels:
			chat.partChannel(token=userToken, channel=i)

		# Enqueue our disconnection to everyone else
		glob.tokens.enqueueAll(serverPackets.userLogout(userID))

		# Disconnect from IRC if needed
		if userToken.irc == True and glob.irc == True:
			glob.ircServer.forceDisconnection(userToken.username)

		# Delete token
		glob.tokens.deleteToken(requestToken)

		# Console output
		log.info("{} has been disconnected.".format(username))
