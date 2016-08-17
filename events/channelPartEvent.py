from constants import clientPackets
from helpers import chatHelper as chat

def handle(userToken, packetData):
	# Channel join packet
	packetData = clientPackets.channelPart(packetData)
	chat.partChannel(token=userToken, channel=packetData["channel"])