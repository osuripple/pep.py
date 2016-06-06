import threading

class fileLocks:
	def __init__(self):
		# Dictionary containing threading.Lock s
		self.locks = {}

	def lockFile(self, fileName):
		if fileName in self.locks:
			# Acquire existing lock
			self.locks[fileName].acquire()
		else:
			# Create new lock and acquire it
			self.locks[fileName] = threading.Lock()
			self.locks[fileName].acquire()

	def unlockFile(self, fileName):
		if fileName in self.locks:
			# Release lock if it exists
			self.locks[fileName].release()
