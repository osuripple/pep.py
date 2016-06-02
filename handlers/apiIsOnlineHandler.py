from helpers import requestHelper
from constants import exceptions
import json
from objects import glob

class handler(requestHelper.asyncRequestHandler):
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Check arguments
			if requestHelper.checkArguments(self.request.arguments, ["u"]) == False:
				raise exceptions.invalidArgumentsException()

			# Get online staus
			username = self.get_argument("u")
			if username == None:
				data["result"] = False
			else:
				data["result"] = True if glob.tokens.getTokenFromUsername(username) != None else False

			# Status code and message
			statusCode = 200
			data["message"] = "ok"
		except exceptions.invalidArgumentsException:
			statusCode = 400
			data["message"] = "missing required arguments"
		finally:
			# Add status code to data
			data["status"] = statusCode

			# Send response
			self.clear()
			self.set_status(statusCode)
			self.finish(json.dumps(data))
