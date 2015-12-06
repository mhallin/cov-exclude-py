import hashlib

from .compat import IO_ERRORS


class FileHashCache:
    def __init__(self, initial_data):
        self.file_hashes = {}

        self.previous_file_hashes = {}

        if initial_data:
            self.previous_file_hashes = initial_data

    def hash_missing_files(self, filenames):
        self.file_hashes.update({
            filename: _hash_file(filename)
            for filename in filenames
            if filename not in self.file_hashes
        })

    def is_identical(self, filename):
        if filename not in self.file_hashes:
            self.file_hashes[filename] = _hash_file(filename)

        old_hash = self.previous_file_hashes.get(filename)
        new_hash = self.file_hashes[filename]

        return old_hash and new_hash and old_hash == new_hash

    def to_json(self):
        return self.file_hashes


def _hash_file(filename):
    try:
        with open(filename, 'rb') as f:
            return hashlib \
                .new('sha1', f.read()) \
                .hexdigest()
    except IO_ERRORS:
        return None
