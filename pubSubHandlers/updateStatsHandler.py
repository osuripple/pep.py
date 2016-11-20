from common.redis import generalPubSubHandler
from objects import glob

class handler(generalPubSubHandler.generalPubSubHandler):
	def __init__(self):
		super().__init__()
		self.type = "int"

	def handle(self, userID):
		userID = super().parseData(userID)
		if userID is None:
			return
		targetToken = glob.tokens.getTokenFromUserID(userID)
		if targetToken is not None:
			targetToken.updateCachedStats()