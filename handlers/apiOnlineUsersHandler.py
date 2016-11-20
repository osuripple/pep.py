import json

from common.web import requestsManager
from objects import glob


class handler(requestsManager.asyncRequestHandler):
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Get online users count
			data["result"] = int(glob.redis.get("ripple:online_users").decode("utf-8"))

			# Status code and message
			statusCode = 200
			data["message"] = "ok"
		finally:
			# Add status code to data
			data["status"] = statusCode

			# Send response
			self.write(json.dumps(data))
			self.set_status(statusCode)
