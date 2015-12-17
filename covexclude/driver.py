from . import linecache
from .compat import IO_ERRORS
from .coverageprocessor import (add_to_cache,
                                determine_non_measured_lines,
                                get_lines_in_file)

FAILED_TESTS_KEY = 'failed_tests'
RECORDED_LINES_KEY = 'recorded_lines'


class Driver:
    def __init__(self, line_cache, file_hash_cache, initial_data):
        self.file_contents_cache = {}

        self.previously_failed_tests = frozenset()
        self.failed_tests = set()

        self.previously_recorded_lines = {}
        self.recorded_lines = {}

        self.line_cache = line_cache
        self.file_hash_cache = file_hash_cache

        if initial_data:
            self.previously_failed_tests = frozenset(
                initial_data.get(FAILED_TESTS_KEY, []))

            self.previously_recorded_lines = initial_data.get(
                RECORDED_LINES_KEY, {})

    def cache_files_from_coverage(self, coverage_data):
        for filename in coverage_data.measured_files():
            try:
                add_to_cache(filename, self.file_contents_cache)
            except IO_ERRORS:
                continue

        self.file_hash_cache.hash_missing_files(coverage_data.measured_files())

    def report_test_coverage(self, item_id, coverage_data):
        indices, non_measured_lines = determine_non_measured_lines(
            coverage_data, self.line_cache)

        test_lines = {
            filename: get_lines_in_file(
                filename,
                lines,
                self.file_contents_cache)
            for filename, lines in non_measured_lines.items()
            if lines
        }

        for filename, ranges in test_lines.items():
            filename_index = self.line_cache.filename_index(filename)
            for start, end, content in ranges:
                indices.append(
                    self.line_cache.save_record(
                        filename_index, start, end, content))

        assert item_id not in self.recorded_lines
        self.recorded_lines[item_id] = indices

    def report_test_failure(self, item_id):
        self.failed_tests.add(item_id)

    def should_execute_item(self, item_id, known_identical_items):
        if item_id not in self.previously_recorded_lines:
            return True

        if item_id in self.previously_failed_tests:
            return True

        old_file_data = self.previously_recorded_lines[item_id]

        for key in old_file_data:
            if key in known_identical_items:
                continue

            filename_index, start, end, content = self.line_cache.lookup(key)
            filename = self.line_cache.filenames[filename_index]

            if self.file_hash_cache.is_identical(filename):
                known_identical_items.add(key)
                continue

            new_line_data = get_lines_in_file(
                filename,
                range(start, end),
                self.file_contents_cache)

            if len(new_line_data) != 1:
                return True

            _, _, expected_content = new_line_data[0]

            if content != linecache.hash(expected_content):
                return True

        return False

    def to_json(self):
        line_data = {}
        line_data.update(self.previously_recorded_lines)
        line_data.update(self.recorded_lines)

        return {
            FAILED_TESTS_KEY: list(self.failed_tests),
            RECORDED_LINES_KEY: line_data,
        }
