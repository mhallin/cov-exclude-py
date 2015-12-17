from .compat import IO_ERRORS


def determine_non_measured_lines(coverage_data, line_cache):
    """Given some coverage data and the line cache, determine which lines
    in which files need to be looked up by scanning the file itself.

    Returns a tuple:
    - A list of line cache keys that already have been scanned and
      determined to be needed by the coverage data.
    - A dictionary mapping from filename to a (sorted) list of lines
      that need to be extracted from the file itself.

    """

    indices = []
    non_measured_lines = {}

    for filename in coverage_data.measured_files():
        filename_index = line_cache.filename_index(filename)
        lines = [i - 1 for i in list(sorted(coverage_data.lines(filename)))]
        actual_lines = []

        next_end = None
        for start in lines:
            if next_end is not None and start >= next_end:
                next_end = None

            if next_end is None:
                key, record = line_cache.match_record(
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

    return indices, non_measured_lines


def add_to_cache(filename, file_contents_cache):
    if filename not in file_contents_cache:
        with open(filename, 'r') as f:
            file_contents_cache[filename] = f.readlines()


def get_lines_in_file(filename, line_numbers, file_contents_cache):
    """Collects "runs" in a Python source file, based on coverage data. A
    "run" is defined as consecutive lines in the coverage data, *plus*
    extra whitespace (including EOF) after any lines in the coverage
    data.

    For example:

    1. def test():
    2.     assert True
    3.
    4.     assert True
    5.
    6.

    If the coverage data includes the lines {2, 4}, this function will
    convert this into {2, 3, 4, 5, 6}. The reason for finding
    determining this data is so that we can detect when lines *not*
    included by the coverage data, but still part of execution, are
    changed. If we only look at the coverage data, we would miss
    changes made in the whitespace in between executed lines.

    """
    lines = []
    line_numbers = frozenset(line_numbers)
    added_previous_line = False

    try:
        add_to_cache(filename, file_contents_cache)
    except IO_ERRORS:
        return []

    all_lines = file_contents_cache[filename]
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
