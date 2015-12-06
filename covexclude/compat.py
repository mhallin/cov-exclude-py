try:
    IO_ERRORS = (FileNotFoundError, NotADirectoryError)
except NameError:
    IO_ERRORS = IOError
