import os


class File(object):
    """
    Convenience class for file objects
    """
    def __init__(self, file_contents, filename):
        # self.path = filepath
        self.file_contents = file_contents
        self.name = filename
        self.size = len(file_contents)

        self.id = None
        self.part_numbers = 0
        self.chunk_size = 0
