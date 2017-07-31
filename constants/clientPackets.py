from constants import dataTypes
from helpers import packetHelper
from constants import slotStatuses


""" Users listing packets """
def userActionChange(stream):
	return packetHelper.readPacketData(stream,
	[
		["actionID", dataTypes.BYTE],
		["actionText", dataTypes.STRING],
		["actionMd5", dataTypes.STRING],
		["actionMods", dataTypes.UINT32],
		["gameMode", dataTypes.BYTE],
		["beatmapID", dataTypes.SINT32]
	])

def userStatsRequest(stream):
	return packetHelper.readPacketData(stream, [["users", dataTypes.INT_LIST]])

def userPanelRequest(stream):
	return packetHelper.readPacketData(stream, [["users", dataTypes.INT_LIST]])


""" Client chat packets """
def sendPublicMessage(stream):
	return packetHelper.readPacketData(stream,
	[
		["unknown", dataTypes.STRING],
		["message", dataTypes.STRING],
		["to", dataTypes.STRING]
	])

def sendPrivateMessage(stream):
	return packetHelper.readPacketData(stream,
	[
		["unknown", dataTypes.STRING],
		["message", dataTypes.STRING],
		["to", dataTypes.STRING],
		["unknown2", dataTypes.UINT32]
	])

def setAwayMessage(stream):
	return packetHelper.readPacketData(stream,
	[
		["unknown", dataTypes.STRING],
		["awayMessage", dataTypes.STRING]
	])

def channelJoin(stream):
	return packetHelper.readPacketData(stream, [["channel", dataTypes.STRING]])

def channelPart(stream):
	return packetHelper.readPacketData(stream, [["channel", dataTypes.STRING]])

def addRemoveFriend(stream):
	return packetHelper.readPacketData(stream, [["friendID", dataTypes.SINT32]])


""" Spectator packets """
def startSpectating(stream):
	return packetHelper.readPacketData(stream, [["userID", dataTypes.SINT32]])


""" Multiplayer packets """
def matchSettings(stream):
	# Data to return, will be merged later
	data = []

	# Some settings
	struct = [
		["matchID", dataTypes.UINT16],
		["inProgress", dataTypes.BYTE],
		["unknown", dataTypes.BYTE],
		["mods", dataTypes.UINT32],
		["matchName", dataTypes.STRING],
		["matchPassword", dataTypes.STRING],
		["beatmapName", dataTypes.STRING],
		["beatmapID", dataTypes.UINT32],
		["beatmapMD5", dataTypes.STRING]
	]

	# Slot statuses (not used)
	for i in range(0,16):
		struct.append(["slot{}Status".format(str(i)), dataTypes.BYTE])

	# Slot statuses (not used)
	for i in range(0,16):
		struct.append(["slot{}Team".format(str(i)), dataTypes.BYTE])

	# Read first part
	data.append(packetHelper.readPacketData(stream, struct))

	# Skip userIDs because fuck
	start = 7+2+1+1+4+4+16+16+len(data[0]["matchName"])+len(data[0]["matchPassword"])+len(data[0]["beatmapMD5"])+len(data[0]["beatmapName"])
	start += 1 if (data[0]["matchName"] == "") else 2
	start += 1 if (data[0]["matchPassword"] == "") else 2
	start += 2	# If beatmap name and MD5 don't change, the client sends \x0b\x00 istead of \x00 only, so always add 2. ...WHY!
	start += 2
	for i in range(0,16):
		s = data[0]["slot{}Status".format(str(i))]
		if s != slotStatuses.FREE and s != slotStatuses.LOCKED:
			start += 4

	# Other settings
	struct = [
		["hostUserID", dataTypes.SINT32],
		["gameMode", dataTypes.BYTE],
		["scoringType", dataTypes.BYTE],
		["teamType", dataTypes.BYTE],
		["freeMods", dataTypes.BYTE],
	]

	# Read last part
	data.append(packetHelper.readPacketData(stream[start:], struct, False))

	result = {}
	for i in data:
		result.update(i)
	return result

def createMatch(stream):
	return matchSettings(stream)

def changeMatchSettings(stream):
	return matchSettings(stream)

def changeSlot(stream):
	return packetHelper.readPacketData(stream, [["slotID", dataTypes.UINT32]])

def joinMatch(stream):
	return packetHelper.readPacketData(stream, [["matchID", dataTypes.UINT32], ["password", dataTypes.STRING]])

def changeMods(stream):
	return packetHelper.readPacketData(stream, [["mods", dataTypes.UINT32]])

def lockSlot(stream):
	return packetHelper.readPacketData(stream, [["slotID", dataTypes.UINT32]])

def transferHost(stream):
	return packetHelper.readPacketData(stream, [["slotID", dataTypes.UINT32]])

def matchInvite(stream):
	return packetHelper.readPacketData(stream, [["userID", dataTypes.UINT32]])

def matchFrames(stream):
	return packetHelper.readPacketData(stream,
	[
		["time", dataTypes.SINT32],
		["id", dataTypes.BYTE],
		["count300", dataTypes.UINT16],
		["count100", dataTypes.UINT16],
		["count50", dataTypes.UINT16],
		["countGeki", dataTypes.UINT16],
		["countKatu", dataTypes.UINT16],
		["countMiss", dataTypes.UINT16],
		["totalScore", dataTypes.SINT32],
		["maxCombo", dataTypes.UINT16],
		["currentCombo", dataTypes.UINT16],
		["perfect", dataTypes.BYTE],
		["currentHp", dataTypes.BYTE],
		["tagByte", dataTypes.BYTE],
		["usingScoreV2", dataTypes.BYTE]
	])

def tournamentMatchInfoRequest(stream):
	return packetHelper.readPacketData(stream, [["matchID", dataTypes.UINT32]])

def tournamentJoinMatchChannel(stream):
	return packetHelper.readPacketData(stream, [["matchID", dataTypes.UINT32]])

def tournamentLeaveMatchChannel(stream):
	return packetHelper.readPacketData(stream, [["matchID", dataTypes.UINT32]])