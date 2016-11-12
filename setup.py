from setuptools import setup

setup(name='realtime_tornado',
      version='0.1',
      description='Websocket handling with tornado',
      url='https://github.com/faderskd/Real-Time-Tornado',
      author='Daniel Fąderski',
      author_email='daniel.faderski@gmail.com',
      license='MIT',
      packages=['realtime_tornado'],
      install_requires=[
        'tornado==4.4.2',
        'redis==2.10.5'
      ],
      zip_safe=False)