import hashlib

FILENAMES_KEY = 'filenames'
RECORDED_RANGES_KEY = 'recorded_ranges'


class LineCache:
    def __init__(self, initial_data):
        # [filename]
        self.filenames = []

        # filename => index
        self.filename_indices = {}

        # [(filename_index, start, end, md5(content))]
        self.recorded_ranges = []

        # (filename, start) => index
        self.range_indices = {}

        if initial_data:
            self.filenames = initial_data[FILENAMES_KEY]
            self.recorded_ranges = initial_data[RECORDED_RANGES_KEY]

            for i, f in enumerate(self.filenames):
                self.filename_indices[f] = i

            for i, (n, s, e, _) in enumerate(self.recorded_ranges):
                self.range_indices[n, s] = i

    def save_record(self, filename_index, start, end, content):
        hashed_content = hash(content)

        t = (filename_index, start)

        if t not in self.range_indices:
            i = len(self.range_indices)
            self.recorded_ranges.append(t + (end, hashed_content, ))
            self.range_indices[t] = i
        else:
            i = self.range_indices[t]
            _, _, saved_end, saved_content = self.recorded_ranges[i]

            assert saved_end == end
            assert saved_content == hashed_content

        return self.range_indices[t]

    def lookup(self, key):
        return self.recorded_ranges[key]

    def match_record(self, filename_index, start):
        i = self.range_indices.get((filename_index, start))

        if i is None:
            return None, None

        return i, self.recorded_ranges[i]

    def filename_index(self, filename):
        if filename not in self.filename_indices:
            i = len(self.filenames)
            self.filenames.append(filename)
            self.filename_indices[filename] = i

        return self.filename_indices[filename]

    def to_json(self):
        return {
            FILENAMES_KEY: self.filenames,
            RECORDED_RANGES_KEY: self.recorded_ranges,
        }


def hash(content):
    return hashlib \
        .new('md5', content.encode('utf-8')) \
        .hexdigest()
