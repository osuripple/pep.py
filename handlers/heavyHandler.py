import tornado.gen
import tornado.web
from common.web import requestsManager
from objects import glob
import time

class handler(requestsManager.asyncRequestHandler):
	@tornado.web.asynchronous
	@tornado.gen.engine
	def asyncGet(self):
		if not glob.debug:
			self.write("Nope")
			return
		time.sleep(0.5)
		self.write("meemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeemmeem")
		self.set_status(200)
		self.add_header("cho-token", "tua madre")
		self.add_header("cho-protocol", "19")
		self.add_header("Connection", "keep-alive")
		self.add_header("Keep-Alive", "timeout=5, max=100")
		self.add_header("Content-Type", "text/html; charset=UTF-8")
		#glob.db.fetchAll("SELECT SQL_NO_CACHE * FROM beatmaps")
		#glob.db.fetchAll("SELECT SQL_NO_CACHE * FROM users")
		#glob.db.fetchAll("SELECT SQL_NO_CACHE * FROM scores")
		#self.write("ibmd")
