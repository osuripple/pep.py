from constants import clientPackets
from helpers import chatHelper as chat

def handle(userToken, packetData):
	# Send private message packet
	packetData = clientPackets.sendPrivateMessage(packetData)
	chat.sendMessage(token=userToken, to=packetData["to"], message=packetData["message"])
