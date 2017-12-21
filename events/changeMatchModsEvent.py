from common.constants import mods
from constants import clientPackets
from constants import matchModModes
from objects import glob


def handle(userToken, packetData):
	# Get token data
	userID = userToken.userID

	# Get packet data
	packetData = clientPackets.changeMods(packetData)

	# Make sure the match exists
	matchID = userToken.matchID
	if matchID not in glob.matches.matches:
		return

	# Set slot or match mods according to modType
	with glob.matches.matches[matchID] as match:
		if match.matchModMode == matchModModes.FREE_MOD:
			# Freemod
			# Host can set global DT/HT
			if userID == match.hostUserID:
				# If host has selected DT/HT and Freemod is enabled, set DT/HT as match mod
				if (packetData["mods"] & mods.DOUBLETIME) > 0:
					match.changeMods(mods.DOUBLETIME)
					# Nightcore
					if (packetData["mods"] & mods.NIGHTCORE) > 0:
						match.changeMods(match.mods + mods.NIGHTCORE)
				elif (packetData["mods"] & mods.HALFTIME) > 0:
					match.changeMods(mods.HALFTIME)
				else:
					# No DT/HT, set global mods to 0 (we are in freemod mode)
					match.changeMods(0)

			# Set slot mods
			slotID = match.getUserSlotID(userID)
			if slotID is not None:
				match.setSlotMods(slotID, packetData["mods"])
		else:
			# Not freemod, set match mods
			match.changeMods(packetData["mods"])
