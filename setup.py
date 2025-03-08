"""Setup for AoE2 Betting Client and mgz Replay Parser."""
from setuptools import setup, find_packages

setup(
    name='aoe2-betting-client',
    version='0.1.0',
    description='Parse Age of Empires 2 recorded games and integrate with a betting dapp.',
    url='https://github.com/happyleavesaoc/aoc-mgz/',
    license='MIT',
    author='happyleaves',
    author_email='happyleaves.tfr@gmail.com',
    packages=find_packages(),
    install_requires=[
        'aocref>=2.0.20',
        'construct==2.8.16',
        'dataclasses==0.8; python_version < "3.7"',
        'tabulate>=0.9.0',
        'requests',
        'flask',
        'watchdog'
    ],
    entry_points={
        'console_scripts': [
            'mgz=mgz.cli:main',
            'aoe2client=client:process_replay',  # One-off processing of a replay file
            # Uncomment the next line if you add a main() to your watcher script:
            # 'aoe2watch=watch_replays:main',
        ],
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ]
)
