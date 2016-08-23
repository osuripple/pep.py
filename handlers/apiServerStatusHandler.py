from helpers import requestHelper
import json
from objects import glob

class handler(requestHelper.asyncRequestHandler):
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Get online users count
			data["result"] = -1 if glob.restarting == True else 1

			# Status code and message
			statusCode = 200
			data["message"] = "ok"
		finally:
			# Add status code to data
			data["status"] = statusCode

			# Send response
			#self.clear()
			self.write(json.dumps(data))
			self.set_status(statusCode)
			#self.finish(json.dumps(data))
