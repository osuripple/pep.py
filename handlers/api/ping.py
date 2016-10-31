from common.web.api import api

class handler(api.asyncAPIHandler):
	@api.api
	@api.args("ses")
	def asyncGet(self):
		self.data["message"] = "狂乱 Hey Kids!!"