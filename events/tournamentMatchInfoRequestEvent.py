from constants import clientPackets
from objects import glob

def handle(userToken, packetData):
	packetData = clientPackets.tournamentMatchInfoRequest(packetData)
	matchID = packetData["matchID"]
	if matchID not in glob.matches.matches or not userToken.tournament:
		return
	with glob.matches.matches[matchID] as m:
		userToken.enqueue(m.matchDataCache)