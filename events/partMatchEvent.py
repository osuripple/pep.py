from objects import glob
from helpers import chatHelper as chat
from constants import serverPackets

def handle(userToken, _):
	# get data from usertoken
	userID = userToken.userID

	# Get match ID and match object
	matchID = userToken.matchID

	# Make sure we are in a match
	if matchID == -1:
		return

	# Make sure the match exists
	if matchID not in glob.matches.matches:
		return

	# The match exists, get object
	match = glob.matches.matches[matchID]

	# Set slot to free
	match.userLeft(userID)

	# Part #multiplayer channel
	chat.partChannel(token=userToken, channel="#multi_{}".format(matchID))

	# Set usertoken match to -1
	userToken.partMatch()
