import hashlib


class LineCache:
    def __init__(self, initial_data):
        # [(filename, start, end, md5(content))]
        self.recorded_ranges = []

        # (filename, start, end) => index
        self.range_indices = {}

        if initial_data:
            self.recorded_ranges = initial_data

            for i, (n, s, e, _) in enumerate(initial_data):
                self.range_indices[n, s, e] = i

    def save_record(self, filename, start, end, content):
        hashed_content = hash(content)

        t = (filename, start, end)

        if t not in self.range_indices:
            i = len(self.range_indices)
            self.recorded_ranges.append(t + (hashed_content, ))
            self.range_indices[t] = i
        else:
            _, _, _, expected = self.recorded_ranges[self.range_indices[t]]

            assert expected == hashed_content

        return self.range_indices[t]

    def lookup(self, key):
        return self.recorded_ranges[key]

    def to_json(self):
        return self.recorded_ranges


def hash(content):
    return hashlib \
        .new('md5', content.encode('utf-8')) \
        .hexdigest()
