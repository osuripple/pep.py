from helpers import requestHelper
from helpers import logHelper as log
import json
from objects import glob
from constants import exceptions

class handler(requestHelper.asyncRequestHandler):
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Check arguments
			if requestHelper.checkArguments(self.request.arguments, ["u"]) == False:
				raise exceptions.invalidArgumentsException()

			# Get userID and its verified cache thing
			# -1: Not in cache
			# 0: Not verified (multiacc)
			# 1: Verified
			userID = self.get_argument("u")
			data["result"] = -1 if userID not in glob.verifiedCache else glob.verifiedCache[userID]

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
			self.add_header("Access-Control-Allow-Origin", "*")
			self.add_header("Content-Type", "application/json")

			# jquery meme
			output = ""
			if "callback" in self.request.arguments:
				output += self.get_argument("callback")+"("
			output += json.dumps(data)
			if "callback" in self.request.arguments:
				output += ")"

			self.write(output)
			self.set_status(statusCode)
