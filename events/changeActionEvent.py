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
	if userHelper.isBanned(userID) == True:
		userToken.enqueue(serverPackets.loginBanned())
		return

	# Send restricted message if needed
	if userToken.restricted == False:
		if userHelper.isRestricted(userID) == True:
			userToken.setRestricted()

	# Change action packet
	packetData = clientPackets.userActionChange(packetData)

	# Update cached stats if our pp changedm if we've just submitted a score or we've changed gameMode
	if (userToken.actionID == actions.playing or userToken.actionID == actions.multiplaying) or (userToken.pp != userHelper.getPP(userID, userToken.gameMode)) or (userToken.gameMode != packetData["gameMode"]):
		log.debug("!!!! UPDATING CACHED STATS !!!!")
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

		if token != None:
			token.enqueue(serverPackets.userPanel(userID))
			token.enqueue(serverPackets.userStats(userID))

	# TODO: Enqueue all if we've changed game mode, (maybe not needed because it's cached)
	#glob.tokens.enqueueAll(serverPackets.userPanel(userID))
	#glob.tokens.enqueueAll(serverPackets.userStats(userID))

	# Send osu!direct alert if needed
	# NOTE: Remove this when osu!direct will be fixed
	if userToken.actionID == actions.osuDirect and userToken.osuDirectAlert == False:
		userToken.osuDirectAlert = True
		userToken.enqueue(serverPackets.sendMessage("FokaBot", userToken.username, "Sup! osu!direct works, but you'll need to update the switcher to have the Download button working. If you didn't update the switcher yet, please do!"))


	# Console output
	log.info("{} changed action: {} [{}][{}]".format(username, str(userToken.actionID), userToken.actionText, userToken.actionMd5))
