from constants import clientPackets
from helpers import chatHelper as chat

def handle(userToken, packetData):
	# Send public message packet
	packetData = clientPackets.sendPublicMessage(packetData)
	chat.sendMessage(token=userToken, to=packetData["to"], message=packetData["message"])
