from helpers import requestHelper
from constants import exceptions
import json
from objects import glob
from helpers import consoleHelper
from constants import bcolors
from helpers import systemHelper

class handler(requestHelper.asyncRequestHandler):
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Check arguments
			if requestHelper.checkArguments(self.request.arguments, ["k"]) == False:
				raise exceptions.invalidArgumentsException()

			# Check ci key
			key = self.get_argument("k")
			if key is None or key != glob.conf.config["ci"]["key"]:
				raise exceptions.invalidArgumentsException()

			consoleHelper.printColored("[!] Ci event triggered!!", bcolors.PINK)
			systemHelper.scheduleShutdown(5, False, "A new Bancho update is available and the server will be restarted in 5 seconds. Thank you for your patience.")

			# Status code and message
			statusCode = 200
			data["message"] = "ok"
		except exceptions.invalidArgumentsException:
			statusCode = 400
			data["message"] = "invalid ci key"
		finally:
			# Add status code to data
			data["status"] = statusCode

			# Send response
			self.clear()
			self.set_status(statusCode)
			self.finish(json.dumps(data))
