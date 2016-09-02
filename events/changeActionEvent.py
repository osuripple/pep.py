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
	if userHelper.isBanned(userID):
		userToken.enqueue(serverPackets.loginBanned())
		return

	# Send restricted message if needed
	if not userToken.restricted:
		if userHelper.isRestricted(userID):
			userToken.setRestricted()

	# Change action packet
	packetData = clientPackets.userActionChange(packetData)

	# If we are not in spectate status but we're spectating someone, stop spectating
	#if userToken.spectating != 0 and userToken.actionID != actions.watching and userToken.actionID != actions.idle and userToken.actionID != actions.afk:
	#	userToken.stopSpectating()

	# If we are not in multiplayer but we are in a match, part match
	#if userToken.matchID != -1 and userToken.actionID != actions.multiplaying and userToken.actionID != actions.multiplayer and userToken.actionID != actions.afk:
	#	userToken.partMatch()

	# Update cached stats if our pp changedm if we've just submitted a score or we've changed gameMode
	if (userToken.actionID == actions.PLAYING or userToken.actionID == actions.MULTIPLAYING) or (userToken.pp != userHelper.getPP(userID, userToken.gameMode)) or (userToken.gameMode != packetData["gameMode"]):
		# Always update game mode, or we'll cache stats from the wrong game mode if we've changed it
		userToken.gameMode = packetData["gameMode"]
		userToken.updateCachedStats()

	# Always update action id, text and md5
	userToken.actionID = packetData["actionID"]
	userToken.actionText = packetData["actionText"]
	userToken.actionMd5 = packetData["actionMd5"]
	userToken.actionMods = packetData["actionMods"]

	# Enqueue our new user panel and stats to us and our spectators
	recipients = [userID]
	if len(userToken.spectators) > 0:
		recipients += userToken.spectators

	for i in recipients:
		if i == userID:
			# Save some loops
			token = userToken
		else:
			token = glob.tokens.getTokenFromUserID(i)

		if token is not None:
			# Force our own packet
			force = True if token.userID == userID else False
			token.enqueue(serverPackets.userPanel(userID, force))
			token.enqueue(serverPackets.userStats(userID, force))

	# Console output
	log.info("{} changed action: {} [{}][{}]".format(username, str(userToken.actionID), userToken.actionText, userToken.actionMd5))
