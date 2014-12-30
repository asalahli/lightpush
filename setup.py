import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages


setup(
    name = 'lightpush',
    version = '0.3.0',
    packages = find_packages(),

    entry_points = {
        'console_scripts': [
            'lightpush = lightpush.main:main'
        ]
    },
    
    author = 'Azad Salahli',
    author_email = 'azadsalahli@gmail.com',
    description = 'A lightweight push notification server for websites.',
    license = 'MIT',
    keywords = 'push notification websockets webserver',
)
