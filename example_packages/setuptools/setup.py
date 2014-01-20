from setuptools import setup, find_packages

setup(
    name='Test Package',
    version="1.1.0",
    author='Continuum Analytics',
    author_email='sean.ross-ross@continuum.io',
    description='Testing the conda build',
    packages=find_packages(),
    install_requires=['Flask', 'werkzeug'],
    entry_points={
        'console_scripts' : [
            'script1 = package1.scripts:main'
            ]
    }
)
