import json

import tornado.web
import tornado.gen

from common.sentry import sentry
from common.web import requestsManager
from constants import exceptions
from helpers import chatHelper
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
			if not requestsManager.checkArguments(self.request.arguments, ["k", "to", "msg"]):
				raise exceptions.invalidArgumentsException()

			# Check ci key
			key = self.get_argument("k")
			if key is None or key != glob.conf.config["server"]["cikey"]:
				raise exceptions.invalidArgumentsException()

			chatHelper.sendMessage(
				"FokaBot",
				self.get_argument("to").encode().decode("ASCII", "ignore"),
				self.get_argument("msg").encode().decode("ASCII", "ignore")
			)

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
			self.write(json.dumps(data))
			self.set_status(statusCode)