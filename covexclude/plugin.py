import coverage
import hashlib
import ujson

from . import linecache

CACHE_KEY = 'cache/coverage-by-test'
CACHE_VERSION_KEY = 'version'
CACHE_VERSION = 4
CACHE_RECORDED_LINES_KEY = 'recorded_lines'
CACHE_FAILED_TESTS = 'failed_tests'
CACHE_FILE_HASHES = 'file_hashes'
CACHE_LINE_CACHE_KEY = 'line_cache'


class CoverageExclusionPlugin:
    def __init__(self, config):
        assert config.cache

        self.config = config
        self.current_cov = None

        cache_data = ujson.loads(config.cache.get(CACHE_KEY, '{}'))
        if cache_data.get(CACHE_VERSION_KEY) != CACHE_VERSION:
            cache_data = {}

        self.line_cache = linecache.LineCache(
            cache_data.get(CACHE_LINE_CACHE_KEY))

        self.previously_recorded_lines = cache_data.get(
            CACHE_RECORDED_LINES_KEY,
            {}
        )

        self.recorded_lines = {}

        self.previously_failed_tests = frozenset(cache_data.get(
            CACHE_FAILED_TESTS,
            []
        ))

        self.failed_tests = set()

        self.previous_file_hashes = cache_data.get(
            CACHE_FILE_HASHES,
            {}
        )

        self.file_hashes = {}

        self.file_contents_cache = {}

    def pytest_runtest_call(self, item):
        assert not self.current_cov

        self.current_cov = coverage.Coverage()
        self.current_cov.start()

    def pytest_runtest_teardown(self, item, nextitem):
        if self.current_cov:
            self.current_cov.stop()
            data = self.current_cov.get_data()
            self.current_cov = None

            indices = []

            non_measured_lines = {}
            for filename in data.measured_files():
                filename_index = self.line_cache.filename_index(filename)
                lines = [i - 1 for i in list(sorted(data.lines(filename)))]
                actual_lines = []

                next_end = None
                for start in lines:
                    if next_end is not None and start >= next_end:
                        next_end = None

                    if next_end is None:
                        key, record = self.line_cache.match_record(
                            filename_index, start)

                        if record is not None:
                            indices.append(key)
                            _, _, next_end, _ = record
                        else:
                            actual_lines.append(start)

                    else:
                        if start >= next_end:
                            actual_lines.append(start)
                            next_end = None

                non_measured_lines[filename] = actual_lines

            test_lines = {
                filename: self._get_lines_in_file(
                    filename,
                    lines)
                for filename, lines in non_measured_lines.items()
                if lines
            }

            for filename, ranges in test_lines.items():
                filename_index = self.line_cache.filename_index(filename)
                for start, end, content in ranges:
                    indices.append(
                        self.line_cache.save_record(
                            filename_index, start, end, content))

            assert item.nodeid not in self.recorded_lines
            self.recorded_lines[item.nodeid] = indices

    def pytest_runtest_logreport(self, report):
        if report.failed and 'xfail' not in report.keywords:
            self.failed_tests.add(report.nodeid)

    def pytest_sessionfinish(self, session):
        line_data = {}
        line_data.update(self.previously_recorded_lines)
        line_data.update(self.recorded_lines)

        for filename in self.line_cache.filenames:
            if filename not in self.file_hashes:
                self.file_hashes[filename] = _hash_file(filename)

        self.config.cache.set(CACHE_KEY, ujson.dumps({
            CACHE_VERSION_KEY: CACHE_VERSION,
            CACHE_RECORDED_LINES_KEY: line_data,
            CACHE_FAILED_TESTS: list(self.failed_tests),
            CACHE_FILE_HASHES: self.file_hashes,
            CACHE_LINE_CACHE_KEY: self.line_cache.to_json(),
        }))

    def pytest_collection_modifyitems(self, session, config, items):
        to_keep = []
        to_skip = []

        for item in items:
            if self._should_execute_item(item):
                to_keep.append(item)
            else:
                to_skip.append(item)

        items[:] = to_keep
        config.hook.pytest_deselected(items=to_skip)

    def _get_lines_in_file(self, filename, line_numbers):
        lines = []
        line_numbers = frozenset(line_numbers)
        added_previous_line = False

        if filename not in self.file_contents_cache:
            try:
                with open(filename, 'r') as f:
                    self.file_contents_cache[filename] = f.readlines()

            except (FileNotFoundError, NotADirectoryError):
                return []

        all_lines = self.file_contents_cache[filename]
        run_start = 0
        current_run_lines = []
        for i, l in enumerate(all_lines):
            l = l[:-1]
            if i in line_numbers:
                if not added_previous_line:
                    run_start = i
                current_run_lines.append(l)
                added_previous_line = True

            elif added_previous_line and l.strip() == '':
                current_run_lines.append(l)
                added_previous_line = True

            elif current_run_lines:
                lines.append((run_start, i, '\n'.join(current_run_lines)))
                added_previous_line = False
                current_run_lines = []

            else:
                added_previous_line = False

        # Add EOF marker
        if added_previous_line:
            current_run_lines.append('')
            lines.append((run_start, i + 1, '\n'.join(current_run_lines)))

        return lines

    def _should_execute_item(self, item):
        if item.nodeid not in self.previously_recorded_lines:
            return True

        if item.nodeid in self.previously_failed_tests:
            return True

        old_file_data = self.previously_recorded_lines[item.nodeid]

        for key in old_file_data:
            filename_index, start, end, content = self.line_cache.lookup(key)
            filename = self.line_cache.filenames[filename_index]

            old_hash = self.previous_file_hashes.get(filename)
            new_hash = self._get_current_file_hash(filename)

            if old_hash and new_hash and old_hash == new_hash:
                continue

            new_line_data = self._get_lines_in_file(
                filename,
                range(start, end))

            if len(new_line_data) != 1:
                return True

            _, _, expected_content = new_line_data[0]

            if content != linecache.hash(expected_content):
                return True

        return False

    def _get_current_file_hash(self, filename):
        if filename not in self.file_hashes:
            self.file_hashes[filename] = _hash_file(filename)

        return self.file_hashes[filename]


def _hash_file(filename):
    try:
        with open(filename, 'rb') as f:
            return hashlib \
                .new('sha1', f.read()) \
                .hexdigest()
    except (FileNotFoundError, NotADirectoryError):
        return None


def pytest_configure(config):
    config.pluginmanager.register(
        CoverageExclusionPlugin(config),
        "coverage-exclusion")
