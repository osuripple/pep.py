from objects import glob

class buffer():
	"""
	A file buffer object.
	This buffer caches data in memory and when it's full, it writes the content to a file.
	"""
	def __init__(self, fileName, writeType="a", maxLength=512):
		"""
		A file buffer object

		:param fileName: Path and name of file on disk .
		:param writeType: File write type. Optional. Default: "a" .
		:param maxLength: Max length before writing buffer to disk. Optional. Default: 512.
		"""
		self.content = ""
		self.length = 0
		self.fileName = fileName
		self.writeType = writeType
		self.maxLength = maxLength

	def write(self, newData):
		"""
		Add data to buffer.
		If the total length of the data in buffer is greater than or equal to self.maxLength,
		the content is written on the disk and the buffer resets

		:param newData: Data to append to buffer
		:return:
		"""
		self.content += newData
		self.length += len(newData)
		if self.length >= self.maxLength:
			self.flush()

	def flush(self):
		"""
		Write buffer content to disk and reset its content

		:return:
		"""
		try:
			glob.fLocks.lockFile(self.fileName)
			with open(self.fileName, self.writeType) as f:
				f.write(self.content)
		finally:
			glob.fLocks.unlockFile(self.fileName)

		self.content = ""
		self.length = 0

class buffersList():
	"""
	A list of buffers
	"""
	def __init__(self):
		self.buffers = {}

	def write(self, fileName, content):
		"""
		Write some data to an existing buffer in this list (or create a new one if it doesn't exist).
		If the buffer is full, the data is written to the file and the buffer resets.

		:param fileName: Path of file/buffer
		:param content: New content
		:return:
		"""
		if fileName not in self.buffers:
			self.buffers[fileName] = buffer(fileName)
		self.buffers[fileName].write(content)

	def flushAll(self):
		"""
		Write all buffers to file and flush them

		:return:
		"""
		for _, value in self.buffers.items():
			value.flush()