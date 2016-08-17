from objects import glob
from helpers import logHelper as log
from helpers import chatHelper as chat

def handle(userToken, _):
	# Get usertoken data
	userID = userToken.userID
	username = userToken.username

	# Remove user from users in lobby
	glob.matches.lobbyUserPart(userID)

	# Part lobby channel
	chat.partChannel(channel="#lobby", token=userToken, kick=True)

	# Console output
	log.info("{} has left multiplayer lobby".format(username))
