"""Install the ROS 2 package and its console entry point."""

from setuptools import setup

PACKAGE = 'amo_camera_streamer'

setup(
    name=PACKAGE,
    version='0.1.0',
    packages=[PACKAGE],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{PACKAGE}']),
        (f'share/{PACKAGE}', ['package.xml']),
    ],
    entry_points={
        'console_scripts': ['camera_streamer=amo_camera_streamer.ros_publisher:main']
    },
)
