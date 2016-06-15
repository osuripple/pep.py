from objects import glob
from constants import clientPackets
from constants import serverPackets
from helpers import userHelper
from helpers import logHelper as log
from constants import actions

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

	# Send osu!direct alert if needed
	# NOTE: Remove this when osu!direct will be fixed
	if userToken.actionID == actions.osuDirect and userToken.osuDirectAlert == False:
		userToken.osuDirectAlert = True
		userToken.enqueue(serverPackets.sendMessage("FokaBot", userToken.username, "Sup! osu!direct works, kinda. To download a beatmap, you have to click the \"View listing\" button (the last one) instead of \"Download\". However, if you are on the stable (fallback) branch, it should work also with the \"Download\" button. We'll fix that bug as soon as possibleTM."))

	# Enqueue our new user panel and stats to everyone
	glob.tokens.enqueueAll(serverPackets.userPanel(userID))
	glob.tokens.enqueueAll(serverPackets.userStats(userID))

	# Console output
	log.info("{} changed action: {} [{}][{}]".format(username, str(userToken.actionID), userToken.actionText, userToken.actionMd5))
