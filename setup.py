import os.path
import platform

from setuptools import setup, find_packages

HERE = os.path.dirname(__file__)


def read_version():
    about_data = {}

    with open(os.path.join(HERE, 'covexclude/__about__.py')) as fp:
        exec(fp.read(), about_data)

    return about_data['__version__']


with open(os.path.join(HERE, 'README.rst')) as fp:
    long_description = fp.read()


install_requires = [
    'coverage>=4.0.0,<5.0.0',
]

if platform.python_implementation() != 'PyPy':
    install_requires += [
        'ujson>=1.0,<2.0',
    ]

setup(
    name='pytest-cov-exclude',
    version=read_version(),
    description='Pytest plugin for excluding tests based on coverage data',
    long_description=long_description,

    author='Magnus Hallin',
    author_email='mhallin@fastmail.com',

    url='https://github.com/mhallin/cov-exclude-py',

    license='MIT',

    packages=find_packages(exclude=['tests']),

    package_data={
        '': ['LICENSE', '*.rst'],
    },

    entry_points={
        'pytest11': [
            'cov-exclude = covexclude.plugin',
        ],
    },

    install_requires=install_requires,

    extras_require={
        'dev': [
            'pytest>=2.8.0,<2.9.0',
        ],
        'dist': [
            'twine',
            'wheel',
        ],
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
    ],

    keywords=[
        'cover',
        'coverage',
        'pytest',
        'py.test',
        'performance',
        'speed',
    ]
)
