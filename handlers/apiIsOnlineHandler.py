import json

import tornado.web
import tornado.gen

from common.sentry import sentry
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob


class handler(requestsManager.asyncRequestHandler):
	@tornado.web.asynchronous
	@tornado.gen.engine
	@sentry.captureTornado
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Check arguments
			if "u" not in self.request.arguments and "id" not in self.request.arguments:
				raise exceptions.invalidArgumentsException()

			# Get online staus
			username = None
			userID = None
			if "u" in self.request.arguments:
				#username = self.get_argument("u").lower().replace(" ", "_")
				username = userUtils.safeUsername(self.get_argument("u"))
			else:
				try:
					userID = int(self.get_argument("id"))
				except:
					raise exceptions.invalidArgumentsException()

			if username is None and userID is None:
				data["result"] = False
			else:
				if username is not None:
					data["result"] = True if glob.tokens.getTokenFromUsername(username, safe=True) is not None else False
				else:
					data["result"] = True if glob.tokens.getTokenFromUserID(userID) is not None else False

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
			self.write(json.dumps(data))
			self.set_status(statusCode)
