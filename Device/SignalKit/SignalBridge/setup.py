"""Package definition for the SignalKit ROS 2 bridge (ament_python)."""

from setuptools import find_packages, setup

PACKAGE = 'amode_signal_bridge'

setup(
    name=PACKAGE,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{PACKAGE}']),
        (f'share/{PACKAGE}', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    description='Relay SignalKit traffic light state and commands to AMO Main Control',
    license='TODO',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [f'signal_bridge = {PACKAGE}.bridge_node:main'],
    },
)
