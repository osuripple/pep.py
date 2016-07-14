from constants import clientPackets
from helpers import chatHelper as chat

def handle(userToken, packetData):
	# Channel join packet
	packetData = clientPackets.channelJoin(packetData)
	chat.joinChannel(token=userToken, channel=packetData["channel"])
