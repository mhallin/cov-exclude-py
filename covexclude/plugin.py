import coverage

try:
    import ujson
except ImportError:
    import json as ujson

from . import linecache, filehashcache
from .coverageprocessor import determine_non_measured_lines, get_lines_in_file

CACHE_KEY = 'cache/coverage-by-test'
CACHE_VERSION_KEY = 'version'
CACHE_VERSION = 4
CACHE_RECORDED_LINES_KEY = 'recorded_lines'
CACHE_FAILED_TESTS = 'failed_tests'
CACHE_FILE_HASH_CACHE_KEY = 'file_hashes'
CACHE_LINE_CACHE_KEY = 'line_cache'


class CoverageExclusionPlugin:
    def __init__(self, config):
        assert config.cache

        self.config = config
        self.current_cov = None

        cache_data = ujson.loads(config.cache.get(CACHE_KEY, '{}'))
        if cache_data.get(CACHE_VERSION_KEY) != CACHE_VERSION:
            cache_data = {}

        self.file_hash_cache = filehashcache.FileHashCache(
            cache_data.get(CACHE_FILE_HASH_CACHE_KEY))

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

        self.file_contents_cache = {}

        self.known_identical_items = set()

    def pytest_runtest_setup(self, item):
        assert not self.current_cov

        self.current_cov = coverage.Coverage()
        self.current_cov.start()

    def pytest_runtest_teardown(self, item, nextitem):
        if self.current_cov:
            self.current_cov.stop()
            data = self.current_cov.get_data()
            data.update(item._extra_cov_data)
            self.current_cov = None

            indices, non_measured_lines = determine_non_measured_lines(
                data, self.line_cache)

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

            assert item.nodeid not in self.recorded_lines
            self.recorded_lines[item.nodeid] = indices

    def pytest_runtest_logreport(self, report):
        if report.failed and 'xfail' not in report.keywords:
            self.failed_tests.add(report.nodeid)

    def pytest_sessionfinish(self, session):
        line_data = {}
        line_data.update(self.previously_recorded_lines)
        line_data.update(self.recorded_lines)

        self.file_hash_cache.hash_missing_files(self.line_cache.filenames)

        self.config.cache.set(CACHE_KEY, ujson.dumps({
            CACHE_VERSION_KEY: CACHE_VERSION,
            CACHE_RECORDED_LINES_KEY: line_data,
            CACHE_FAILED_TESTS: list(self.failed_tests),
            CACHE_FILE_HASH_CACHE_KEY: self.file_hash_cache.to_json(),
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

        self.known_identical_items = None

    def pytest_collectstart(self, collector):
        self.collect_cov = coverage.Coverage()
        self.collect_cov.start()

    def pytest_itemcollected(self, item):
        self.collect_cov.stop()
        item._extra_cov_data = self.collect_cov.get_data()

    def _should_execute_item(self, item):
        if item.nodeid not in self.previously_recorded_lines:
            return True

        if item.nodeid in self.previously_failed_tests:
            return True

        if item.get_marker('external_dependencies'):
            return True

        old_file_data = self.previously_recorded_lines[item.nodeid]

        for key in old_file_data:
            if key in self.known_identical_items:
                continue

            filename_index, start, end, content = self.line_cache.lookup(key)
            filename = self.line_cache.filenames[filename_index]

            if self.file_hash_cache.is_identical(filename):
                self.known_identical_items.add(key)
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


def pytest_configure(config):
    config.pluginmanager.register(
        CoverageExclusionPlugin(config),
        "coverage-exclusion")


def _debug_coverage_data(data):
    for filename in data.measured_files():
        if 'site-packages' in filename:
            continue

        print('{}: {}'.format(filename, data.lines(filename)))


def _debug_lines_in_file(filename, data):
    if 'site-packages' in filename:
        return

    print('{}: {}'.format(filename, data))
