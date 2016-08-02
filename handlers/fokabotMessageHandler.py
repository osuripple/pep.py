from helpers import requestHelper
from constants import exceptions
import json
from objects import glob
from helpers import chatHelper
from helpers import logHelper as log

class handler(requestHelper.asyncRequestHandler):
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Check arguments
			if requestHelper.checkArguments(self.request.arguments, ["k", "to", "msg"]) == False:
				raise exceptions.invalidArgumentsException()

			# Check ci key
			key = self.get_argument("k")
			if key is None or key != glob.conf.config["server"]["cikey"]:
				raise exceptions.invalidArgumentsException()

			log.info("API REQUEST FOR FOKABOT MESSAGE AAAAAAA")
			chatHelper.sendMessage("FokaBot", self.get_argument("to"), self.get_argument("msg"))

			# Status code and message
			statusCode = 200
			data["message"] = "ok"
		except exceptions.invalidArgumentsException:
			statusCode = 400
			data["message"] = "invalid parameters"
		finally:
			# Add status code to data
			data["status"] = statusCode

			# Send response
			#self.clear()
			self.write(json.dumps(data))
			self.set_status(statusCode)
			#self.finish(json.dumps(data))
