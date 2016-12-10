import time
import json

from common.log import logUtils as log
from constants import serverPackets
from helpers import chatHelper as chat
from objects import glob


def handle(userToken, _=None, deleteToken=True):
	# get usertoken data
	userID = userToken.userID
	username = userToken.username
	requestToken = userToken.token

	# Big client meme here. If someone logs out and logs in right after,
	# the old logout packet will still be in the queue and will be sent to
	# the server, so we accept logout packets sent at least 5 seconds after login
	# if the user logs out before 5 seconds, he will be disconnected later with timeout check
	if int(time.time() - userToken.loginTime) >= 5 or userToken.irc:
		# Stop spectating
		userToken.stopSpectating()

		# Part matches
		userToken.leaveMatch()
		
		# Part all joined channels
		for i in userToken.joinedChannels:
			chat.partChannel(token=userToken, channel=i)

		# Leave all joined streams
		userToken.leaveAllStreams()

		# Enqueue our disconnection to everyone else
		glob.streams.broadcast("main", serverPackets.userLogout(userID))

		# Disconnect from IRC if needed
		if userToken.irc and glob.irc:
			glob.ircServer.forceDisconnection(userToken.username)

		# Delete token
		if deleteToken:
			glob.tokens.deleteToken(requestToken)
		else:
			userToken.kicked = True

		# Change username if needed
		newUsername = glob.redis.get("ripple:change_username_pending:{}".format(userID))
		if newUsername is not None:
			log.debug("Sending username change request for user {}".format(userID))
			glob.redis.publish("peppy:change_username", json.dumps({
				"userID": userID,
				"newUsername": newUsername.decode("utf-8")
			}))

		# Console output
		log.info("{} has been disconnected. (logout)".format(username))
