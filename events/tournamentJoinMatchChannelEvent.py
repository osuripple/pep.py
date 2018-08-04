from constants import clientPackets
from objects import glob
from helpers import chatHelper as chat

def handle(userToken, packetData):
	packetData = clientPackets.tournamentJoinMatchChannel(packetData)
	matchID = packetData["matchID"]
	if matchID not in glob.matches.matches or not userToken.tournament:
		return
	userToken.matchID = matchID
	chat.joinChannel(token=userToken, channel="#multi_{}".format(matchID), force=True)