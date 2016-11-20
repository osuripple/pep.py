from common.redis import generalPubSubHandler
from objects import glob

class handler(generalPubSubHandler.generalPubSubHandler):
	def __init__(self):
		super().__init__()
		self.structure = {
			"userID": 0,
			"reason": ""
		}

	def handle(self, data):
		data = super().parseData(data)
		if data is None:
			return
		targetToken = glob.tokens.getTokenFromUserID(data["userID"])
		if targetToken is not None:
			targetToken.kick(data["reason"], "pubsub_kick")