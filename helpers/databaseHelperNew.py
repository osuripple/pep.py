import queue
import MySQLdb
from helpers import logHelper as log

class worker():
	"""
	A single MySQL worker
	"""
	def __init__(self, connection, temporary=False):
		"""
		Initialize a MySQL worker

		:param connection: database connection object
		:param temporary: if True, this worker will be flagged as temporary
		"""
		self.connection = connection
		self.temporary = temporary
		log.debug("Created MySQL worker. Temporary: {}".format(self.temporary))

	def ping(self):
		"""
		Ping MySQL server using this worker.

		:return: True if connected, False if error occured.
		"""
		try:
			self.connection.cursor(MySQLdb.cursors.DictCursor).execute("SELECT 1+1")
			return True
		except:
			return False

	def __del__(self):
		"""
		Close connection to the server

		:return:
		"""
		self.connection.close()
		log.debug("Destroyed MySQL worker.")

class connectionsPool():
	"""
	A MySQL workers pool
	"""
	def __init__(self, host, username, password, database, initialSize=16):
		"""
		Initialize a MySQL connections pool

		:param host: MySQL host
		:param username: MySQL username
		:param password: MySQL password
		:param database: MySQL database name
		:param initialSize: initial pool size
		"""
		self.config = (host, username, password, database)
		self.maxSize = initialSize
		self.pool = queue.Queue(0)
		self.consecutiveEmptyPool = 0
		self.fillPool()

	def newWorker(self, temporary=False):
		"""
		Create a new worker.

		:param temporary: if True, flag the worker as temporary
		:return: instance of worker class
		"""
		db = MySQLdb.connect(*self.config)
		db.autocommit(True)
		conn = worker(db, temporary)
		return conn

	def expandPool(self, newWorkers=5):
		"""
		Add some new workers to the pool

		:param newWorkers: number of new workers
		:return:
		"""
		self.maxSize += newWorkers
		self.fillPool()

	def fillPool(self):
		"""
		Fill the queue with workers until its maxSize

		:return:
		"""
		size = self.pool.qsize()
		if self.maxSize > 0 and size >= self.maxSize:
			return
		newConnections = self.maxSize-size
		for _ in range(0, newConnections):
			self.pool.put_nowait(self.newWorker())

	def getWorker(self):
		"""
		Get a MySQL connection worker from the pool.
		If the pool is empty, a new temporary worker is created.

		:return: instance of worker class
		"""

		if self.pool.empty():
			# The pool is empty. Spawn a new temporary worker
			log.warning("Using temporary worker")
			worker = self.newWorker(True)

			# Increment saturation
			self.consecutiveEmptyPool += 1

			# If the pool is usually empty, expand it
			if self.consecutiveEmptyPool >= 5:
				log.warning("MySQL connections pool is saturated. Filling connections pool.")
				self.expandPool()
		else:
			# The pool is not empty. Get worker from the pool
			# and reset saturation counter
			worker = self.pool.get()
			self.consecutiveEmptyPool = 0

		# Return the connection
		return worker

	def putWorker(self, worker):
		"""
		Put the worker back in the pool.
		If the worker is temporary, close the connection
		and destroy the object

		:param worker: worker object
		:return:
		"""
		if worker.temporary:
			del worker
		else:
			self.pool.put_nowait(worker)

class db:
	"""
	A MySQL helper with multiple workers
	"""
	def __init__(self, host, username, password, database, initialSize):
		"""
		Initialize a new MySQL database helper with multiple workers.
		This class is thread safe.

		:param host: MySQL host
		:param username: MySQL username
		:param password: MySQL password
		:param database: MySQL database name
		:param initialSize: initial pool size
		"""
		self.pool = connectionsPool(host, username, password, database, initialSize)

	def execute(self, query, params = ()):
		"""
		Executes a query

		:param query: query to execute. You can bind parameters with %s
		:param params: parameters list. First element replaces first %s and so on
		"""
		log.debug(query)
		cursor = None
		worker = self.pool.getWorker()

		try:
			# Create cursor, execute query and commit
			cursor = worker.connection.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute(query, params)
			return cursor.lastrowid
		except MySQLdb.OperationalError:
			del worker
			worker = None
			self.execute(query, params)
		finally:
			# Close the cursor and release worker's lock
			if cursor is not None:
				cursor.close()
			if worker is not None:
				self.pool.putWorker(worker)

	def fetch(self, query, params = (), all = False):
		"""
		Fetch a single value from db that matches given query

		:param query: query to execute. You can bind parameters with %s
		:param params: parameters list. First element replaces first %s and so on
		:param all: fetch one or all values. Used internally. Use fetchAll if you want to fetch all values
		"""
		log.debug(query)
		cursor = None
		worker = self.pool.getWorker()

		try:
			# Create cursor, execute the query and fetch one/all result(s)
			cursor = worker.connection.cursor(MySQLdb.cursors.DictCursor)
			cursor.execute(query, params)
			if all == True:
				return cursor.fetchall()
			else:
				return cursor.fetchone()
		except MySQLdb.OperationalError:
			del worker
			worker = None
			self.fetch(query, params, all)
		finally:
			# Close the cursor and release worker's lock
			if cursor is not None:
				cursor.close()
			if worker is not None:
				self.pool.putWorker(worker)

	def fetchAll(self, query, params = ()):
		"""
		Fetch all values from db that matche given query.
		Calls self.fetch with all = True.

		:param query: query to execute. You can bind parameters with %s
		:param params: parameters list. First element replaces first %s and so on
		"""
		return self.fetch(query, params, True)
