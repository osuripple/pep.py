from constants import clientPackets
from objects import glob
from helpers import chatHelper as chat

def handle(userToken, packetData):
	packetData = clientPackets.tournamentLeaveMatchChannel(packetData)
	matchID = packetData["matchID"]
	if matchID not in glob.matches.matches or not userToken.tournament:
		return
	chat.partChannel(token=userToken, channel="#multi_{}".format(matchID), force=True)
	userToken.matchID = 0