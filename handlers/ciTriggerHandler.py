from helpers import requestHelper
from constants import exceptions
import json
from objects import glob
from helpers import systemHelper
from helpers import logHelper as log

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
			if key is None or key != glob.conf.config["server"]["cikey"]:
				raise exceptions.invalidArgumentsException()

			log.info("Ci event triggered!!")
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
			self.write(json.dumps(data))
			self.set_status(statusCode)
