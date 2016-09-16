import MySQLdb
import threading
import glob
from helpers import logHelper as log
import threading

class mysqlWorker:
	"""
	Instance of a pettirosso meme
	"""
	def __init__(self, wid, host, username, password, database):
		"""
		Create a pettirosso meme (mysql worker)

		wid -- worker id
		host -- hostname
		username -- MySQL username
		password -- MySQL password
		database -- MySQL database name
		"""
		self.wid = wid
		self.connection = MySQLdb.connect(host, username, password, database)
		self.connection.autocommit(True)
		self.ready = True
		self.lock = threading.Lock()

class db:
	"""
	A MySQL db connection with multiple workers
	"""

	def __init__(self, host, username, password, database, workers):
		"""
		Create MySQL workers aka pettirossi meme

		host -- hostname
		username -- MySQL username
		password -- MySQL password
		database -- MySQL database name
		workers -- Number of workers to spawn
		"""
		self.workers = []
		self.lastWorker = 0
		self.workersNumber = workers
		self.locked = 0
		for i in range(0,self.workersNumber):
			print(".", end="")
			self.workers.append(mysqlWorker(i, host, username, password, database))

	def checkPoolSaturation(self):
		"""
		Check the number of busy connections in connections pool.
		If the pool is 100% busy, log a message to sentry
		"""
		if self.locked >= (self.workersNumber-1):
			msg = "MySQL connections pool is saturated!".format(self.locked, self.workersNumber)
			log.warning(msg)
			glob.application.sentry_client.captureMessage(msg, level="warning", extra={
				"workersBusy": self.locked,
				"workersTotal": self.workersNumber
			})

	def getWorker(self):
		"""
		Return a worker object (round-robin way)

		return -- worker object
		"""
		if self.lastWorker >= self.workersNumber-1:
			self.lastWorker = 0
		else:
			self.lastWorker += 1

		# Saturation check
		threading.Thread(target=self.checkPoolSaturation).start()
		self.locked += 1
		return self.workers[self.lastWorker]

	def execute(self, query, params = ()):
		"""
		Executes a query

		query -- Query to execute. You can bind parameters with %s
		params -- Parameters list. First element replaces first %s and so on. Optional.
		"""
		log.debug(query)
		# Get a worker and acquire its lock
		worker = self.getWorker()
		worker.lock.acquire()

		try:
			# Create cursor, execute query and commit
			cursor = worker.connection.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute(query, params)
			return cursor.lastrowid
		finally:
			# Close the cursor and release worker's lock
			if cursor:
				cursor.close()
			worker.lock.release()
			self.locked -= 1

	def fetch(self, query, params = (), all = False):
		"""
		Fetch a single value from db that matches given query

		query -- Query to execute. You can bind parameters with %s
		params -- Parameters list. First element replaces first %s and so on. Optional.
		all -- Fetch one or all values. Used internally. Use fetchAll if you want to fetch all values.
		"""
		log.debug(query)
		# Get a worker and acquire its lock
		worker = self.getWorker()
		worker.lock.acquire()

		try:
			# Create cursor, execute the query and fetch one/all result(s)
			cursor = worker.connection.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute(query, params)
			if all == True:
				return cursor.fetchall()
			else:
				return cursor.fetchone()
		finally:
			# Close the cursor and release worker's lock
			if cursor:
				cursor.close()
			worker.lock.release()
			self.locked -= 1

	def fetchAll(self, query, params = ()):
		"""
		Fetch all values from db that matche given query.
		Calls self.fetch with all = True.

		query -- Query to execute. You can bind parameters with %s
		params -- Parameters list. First element replaces first %s and so on. Optional.
		"""
		return self.fetch(query, params, True)
