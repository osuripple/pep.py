import glob
import clientPackets
import serverPackets
from constants import actions
import userHelper

def handle(userToken, packetData):
	# Get usertoken data
	userID = userToken.userID
	username = userToken.username

	# Make sure we are not banned
	if userHelper.getAllowed(userID) == 0:
		userToken.enqueue(serverPackets.loginBanned())
		return

	# Change action packet
	packetData = clientPackets.userActionChange(packetData)

	# Update our action id, text and md5
	userToken.actionID = packetData["actionID"]
	userToken.actionText = packetData["actionText"]
	userToken.actionMd5 = packetData["actionMd5"]
	userToken.actionMods = packetData["actionMods"]
	userToken.gameMode = packetData["gameMode"]

	# Enqueue our new user panel and stats to everyone
	glob.tokens.enqueueAll(serverPackets.userPanel(userID))
	glob.tokens.enqueueAll(serverPackets.userStats(userID))

	# Console output
	print("> {} changed action: {} [{}][{}]".format(username, str(userToken.actionID), userToken.actionText, userToken.actionMd5))
