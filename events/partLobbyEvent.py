from common.log import logUtils as log
from helpers import chatHelper as chat

def handle(userToken, _):
	# Get usertoken data
	username = userToken.username

	# Remove user from users in lobby
	userToken.leaveStream("lobby")

	# Part lobby channel
	# Done automatically by the client
	chat.partChannel(channel="#lobby", token=userToken, kick=True)

	# Console output
	log.info("{} has left multiplayer lobby".format(username))
