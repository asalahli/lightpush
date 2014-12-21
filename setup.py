import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

from lightpush.info import *


setup(
    name = project_name,
    version = project_version,
    packages = find_packages(),

    entry_points = {
        'console_scripts': [
            'lightpush = lightpush.main:main'
        ]
    },
    
    author = 'Azad Salahli',
    author_email = 'azadsalahli@gmail.com',
    description = project_description,
    license = 'MIT',
    keywords = 'push notification websockets webserver',
)