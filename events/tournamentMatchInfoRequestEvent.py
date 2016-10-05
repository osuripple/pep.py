from constants import clientPackets
from constants import serverPackets
from objects import glob

def handle(userToken, packetData):
	packetData = clientPackets.tournamentMatchInfoRequest(packetData)
	matchID = packetData["matchID"]
	if matchID not in glob.matches.matches:
		return
	userToken.enqueue(serverPackets.updateMatch(matchID))