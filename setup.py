import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='openimis_be_report_hiv',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    license='GNU AGPL v3',
    description='The openIMIS Invoice Report backend Cameroonian cheque Sante reference module.',
    url='https://openimis.org',
    author='Kevel CHOUMENE',
    author_email='keveltiah@gmail.com',
    install_requires=[
        'django',
        'django-db-signals',
        'djangorestframework',
    ],
    classifiers=[
        'Environment : : Web Environment',
        'Framework :: Django',
        'Framework :: Django',
        'Framework :: Django :: 2.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)