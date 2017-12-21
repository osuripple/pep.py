import random

from common import generalUtils
from common.log import logUtils as log
from constants import clientPackets
from constants import matchModModes
from constants import matchTeamTypes
from constants import matchTeams
from constants import slotStatuses
from objects import glob


def handle(userToken, packetData):
	# Read new settings
	packetData = clientPackets.changeMatchSettings(packetData)

	# Get match ID
	matchID = userToken.matchID
		
	# Make sure the match exists
	if matchID not in glob.matches.matches:
		return

	# Host check
	with glob.matches.matches[matchID] as match:
		if userToken.userID != match.hostUserID:
			return

		# Some dank memes easter egg
		memeTitles = [
			"RWC 2020",
			"Fokabot is a duck",
			"Dank memes",
			"1337ms Ping",
			"Iscriviti a Xenotoze",
			"...e i marò?",
			"Superman dies",
			"The brace is on fire",
			"print_foot()",
			"#FREEZEBARKEZ",
			"Ripple devs are actually cats",
			"Thank Mr Shaural",
			"NEVER GIVE UP",
			"T I E D  W I T H  U N I T E D",
			"HIGHEST HDHR LOBBY OF ALL TIME",
			"This is gasoline and I set myself on fire",
			"Everyone is cheating apparently",
			"Kurwa mac",
			"TATOE",
			"This is not your drama landfill.",
			"I like cheese",
			"NYO IS NOT A CAT HE IS A DO(N)G",
			"Datingu startuato"
		]

		# Set match name
		match.matchName = packetData["matchName"] if packetData["matchName"] != "meme" else random.choice(memeTitles)

		# Update match settings
		match.inProgress = packetData["inProgress"]
		if packetData["matchPassword"] != "":
			match.matchPassword = generalUtils.stringMd5(packetData["matchPassword"])
		else:
			match.matchPassword = ""
		match.beatmapName = packetData["beatmapName"]
		match.beatmapID = packetData["beatmapID"]
		match.hostUserID = packetData["hostUserID"]
		match.gameMode = packetData["gameMode"]

		oldBeatmapMD5 = match.beatmapMD5
		oldMods = match.mods
		oldMatchTeamType = match.matchTeamType

		match.mods = packetData["mods"]
		match.beatmapMD5 = packetData["beatmapMD5"]
		match.matchScoringType = packetData["scoringType"]
		match.matchTeamType = packetData["teamType"]
		match.matchModMode = packetData["freeMods"]

		# Reset ready if needed
		if oldMods != match.mods or oldBeatmapMD5 != match.beatmapMD5:
			match.resetReady()

		# Reset mods if needed
		if match.matchModMode == matchModModes.NORMAL:
			# Reset slot mods if not freeMods
			match.resetMods()
		else:
			# Reset match mods if freemod
			match.mods = 0

		# Initialize teams if team type changed
		if match.matchTeamType != oldMatchTeamType:
			match.initializeTeams()

		# Force no freemods if tag coop
		if match.matchTeamType == matchTeamTypes.TAG_COOP or match.matchTeamType == matchTeamTypes.TAG_TEAM_VS:
			match.matchModMode = matchModModes.NORMAL

		# Send updated settings
		match.sendUpdates()

		# Console output
		log.info("MPROOM{}: Updated room settings".format(match.matchID))
