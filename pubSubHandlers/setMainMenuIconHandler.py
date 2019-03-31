from common.log import logUtils as log
from common.redis import generalPubSubHandler
from objects import glob
from constants import serverPackets


class handler(generalPubSubHandler.generalPubSubHandler):
	def __init__(self):
		super().__init__()
		self.structure = {
			"userID": 0,
			"mainMenuIconID": 0
		}

	def handle(self, data):
		data = super().parseData(data)
		if data is None:
			return
		targetTokens = glob.tokens.getTokenFromUserID(data["userID"], ignoreIRC=True, _all=True)
		if targetTokens:
			icon = glob.db.fetch(
				"SELECT file_id, url FROM main_menu_icons WHERE id = %s LIMIT 1",
				(data["mainMenuIconID"],)
			)
			if icon is None:
				log.warning("Tried to test an unknown main menu icon")
				return
			for x in targetTokens:
				x.enqueue(
					serverPackets.mainMenuIcon("{}|{}".format(
						"https://i.ppy.sh/{}.png".format(icon["file_id"]),
						icon["url"]
					))
				)
