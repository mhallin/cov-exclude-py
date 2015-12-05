import coverage

CACHE_KEY = 'cache/coverage-by-test'
CACHE_VERSION_KEY = 'version'
CACHE_VERSION = 1
CACHE_RECORDED_LINES_KEY = 'recorded_lines'
CACHE_FAILED_TESTS = 'failed_tests'


class CoverageExclusionPlugin:
    def __init__(self, config):
        assert config.cache

        self.config = config
        self.current_cov = None

        cache_data = config.cache.get(CACHE_KEY, {})
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

    def pytest_runtest_call(self, item):
        assert not self.current_cov

        self.current_cov = coverage.Coverage()
        self.current_cov.start()

    def pytest_runtest_teardown(self, item, nextitem):
        assert self.current_cov

        self.current_cov.stop()
        data = self.current_cov.get_data()
        self.current_cov = None

        test_lines = {
            filename: self._get_lines_in_file(filename, data.lines(filename))
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

        self.config.cache.set(CACHE_KEY, {
            CACHE_VERSION_KEY: CACHE_VERSION,
            CACHE_RECORDED_LINES_KEY: line_data,
            CACHE_FAILED_TESTS: list(self.failed_tests),
        })

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

        with open(filename, 'r') as f:
            for i, l in enumerate(f):
                if i + 1 in line_numbers:
                    lines.append((i + 1, l))
                    added_previous_line = True

                elif added_previous_line and l.strip() == '':
                    lines.append((i + 1, l))
                    added_previous_line = True

                else:
                    added_previous_line = False

            # Add EOF marker
            if added_previous_line:
                lines.append((i + 1, ''))

        return lines

    def _should_execute_item(self, item):
        if item.nodeid not in self.previously_recorded_lines:
            return True

        if item.nodeid in self.previously_failed_tests:
            return True

        old_file_data = self.previously_recorded_lines[item.nodeid]

        for filename, old_line_data in old_file_data.items():
            line_numbers = [i for i, _ in old_line_data]
            new_line_data = self._get_lines_in_file(filename, line_numbers)

            if len(old_line_data) != len(new_line_data):
                return True

            for (i1, l1), (i2, l2) in zip(old_line_data, new_line_data):
                if i1 != i2 or l1 != l2:
                    return True

        return False


def pytest_configure(config):
    config.pluginmanager.register(
        CoverageExclusionPlugin(config),
        "coverage-exclusion")
