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
			if "u" not in self.request.arguments or "id" not in self.request.arguments:
				raise exceptions.invalidArgumentsException()

			# Get online staus
			username = None
			userID = None
			if "u" in self.request.arguments:
				username = self.get_argument("u")
			else:
				try:
					userID = int(self.get_argument("id"))
				except:
					raise exceptions.invalidArgumentsException()

			if username == None and userID == None:
				data["result"] = False
			else:
				if username != None:
					data["result"] = True if glob.tokens.getTokenFromUsername(username) != None else False
				else:
					data["result"] = True if glob.tokens.getTokenFromUserID(userID) != None else False

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
			#self.clear()
			self.write(json.dumps(data))
			self.set_status(statusCode)
			#self.finish(json.dumps(data))
