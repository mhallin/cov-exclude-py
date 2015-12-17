import coverage

try:
    import ujson
except ImportError:
    import json as ujson

from . import linecache, filehashcache, driver

CACHE_KEY = 'cache/coverage-by-test'
CACHE_VERSION_KEY = 'version'
CACHE_VERSION = 5
CACHE_FAILED_TESTS = 'failed_tests'
CACHE_FILE_HASH_CACHE_KEY = 'file_hashes'
CACHE_LINE_CACHE_KEY = 'line_cache'
CACHE_DRIVER_KEY = 'driver'


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

        self.driver = driver.Driver(
            self.line_cache,
            self.file_hash_cache,
            cache_data.get(CACHE_DRIVER_KEY))

    def pytest_runtest_setup(self, item):
        assert not self.current_cov

        self.current_cov = coverage.Coverage()
        self.current_cov.start()

    def pytest_runtest_teardown(self, item, nextitem):
        if not self.current_cov:
            return

        self.current_cov.stop()

        data = self.current_cov.get_data()
        self.current_cov = None

        data.update(item._extra_cov_data)

        self.driver.report_test_coverage(item.nodeid, data)

    def pytest_runtest_logreport(self, report):
        if report.failed and 'xfail' not in report.keywords:
            self.driver.report_test_failure(report.nodeid)

    def pytest_sessionfinish(self, session):
        self.file_hash_cache.hash_missing_files(self.line_cache.filenames)

        self.config.cache.set(CACHE_KEY, ujson.dumps({
            CACHE_VERSION_KEY: CACHE_VERSION,
            CACHE_FILE_HASH_CACHE_KEY: self.file_hash_cache.to_json(),
            CACHE_LINE_CACHE_KEY: self.line_cache.to_json(),
            CACHE_DRIVER_KEY: self.driver.to_json(),
        }))

    def pytest_collection_modifyitems(self, session, config, items):
        to_keep = []
        to_skip = []

        known_identical_items = set()

        for item in items:
            if self._should_execute_item(item, known_identical_items):
                to_keep.append(item)
            else:
                to_skip.append(item)

        items[:] = to_keep
        config.hook.pytest_deselected(items=to_skip)

    def pytest_collectstart(self, collector):
        self.collect_cov = coverage.Coverage()
        self.collect_cov.start()

    def pytest_itemcollected(self, item):
        self.collect_cov.stop()
        item._extra_cov_data = self.collect_cov.get_data()

        self.driver.cache_files_from_coverage(self.collect_cov.get_data())

    def _should_execute_item(self, item, known_identical_items):
        if item.get_marker('external_dependencies'):
            return True

        return self.driver.should_execute_item(
            item.nodeid, known_identical_items)


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
