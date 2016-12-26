from constants import clientPackets
from objects import glob

def handle(userToken, packetData):
	packetData = clientPackets.tournamentMatchInfoRequest(packetData)
	matchID = packetData["matchID"]
	if matchID not in glob.matches.matches:
		return
	userToken.enqueue(glob.matches.matches[matchID].matchDataCache)