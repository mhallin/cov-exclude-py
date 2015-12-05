import coverage
import hashlib
import ujson

CACHE_KEY = 'cache/coverage-by-test'
CACHE_VERSION_KEY = 'version'
CACHE_VERSION = 2
CACHE_RECORDED_LINES_KEY = 'recorded_lines'
CACHE_FAILED_TESTS = 'failed_tests'
CACHE_FILE_HASHES = 'file_hashes'


class CoverageExclusionPlugin:
    def __init__(self, config):
        assert config.cache

        self.config = config
        self.current_cov = None

        cache_data = ujson.loads(config.cache.get(CACHE_KEY, '{}'))
        if cache_data.get(CACHE_VERSION_KEY) != CACHE_VERSION:
            cache_data = {}

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

            test_lines = {
                filename: self._get_lines_in_file(
                    filename,
                    [i - 1 for i in data.lines(filename)])
                for filename in data.measured_files()
            }

            assert item.nodeid not in self.recorded_lines
            self.recorded_lines[item.nodeid] = test_lines

    def pytest_runtest_logreport(self, report):
        if report.failed and 'xfail' not in report.keywords:
            self.failed_tests.add(report.nodeid)

    def pytest_sessionfinish(self, session):
        line_data = {}
        line_data.update(self.previously_recorded_lines)
        line_data.update(self.recorded_lines)

        self.config.cache.set(CACHE_KEY, ujson.dumps({
            CACHE_VERSION_KEY: CACHE_VERSION,
            CACHE_RECORDED_LINES_KEY: line_data,
            CACHE_FAILED_TESTS: list(self.failed_tests),
            CACHE_FILE_HASHES: self.file_hashes,
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
                lines.append((run_start, i, _hash_lines(current_run_lines)))
                added_previous_line = False
                current_run_lines = []

            else:
                added_previous_line = False

        # Add EOF marker
        if added_previous_line:
            current_run_lines.append('')
            lines.append((run_start, i + 1, _hash_lines(current_run_lines)))

        return lines

    def _should_execute_item(self, item):
        if item.nodeid not in self.previously_recorded_lines:
            return True

        if item.nodeid in self.previously_failed_tests:
            return True

        old_file_data = self.previously_recorded_lines[item.nodeid]

        for filename, old_line_data in old_file_data.items():
            old_hash = self.previous_file_hashes.get(filename)
            new_hash = self._get_current_file_hash(filename)

            if old_hash and new_hash and old_hash == new_hash:
                continue

            line_numbers = []
            for s, e, _ in old_line_data:
                line_numbers += list(range(s, e))
            new_line_data = self._get_lines_in_file(filename, line_numbers)

            if len(old_line_data) != len(new_line_data):
                return True

            for (s1, e1, l1), (s2, e2, l2) in zip(old_line_data, new_line_data):
                if s1 != s2 or l1 != l2:
                    return True

        return False

    def _get_current_file_hash(self, filename):
        if filename not in self.file_hashes:
            try:
                with open(filename, 'rb') as f:
                    self.file_hashes[filename] = hashlib \
                        .new('sha1', f.read()) \
                        .hexdigest()
            except (FileNotFoundError, NotADirectoryError):
                self.file_hashes[filename] = None

        return self.file_hashes[filename]


def pytest_configure(config):
    config.pluginmanager.register(
        CoverageExclusionPlugin(config),
        "coverage-exclusion")


def _hash_lines(ls):
    return hashlib \
        .new('md5', '\n'.join(ls).encode('utf-8')) \
        .hexdigest()
