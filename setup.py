from setuptools import setup, find_packages

def readme():
    try:
        return open('README.md').read()
    except FileNotFoundError:
        return ''

setup(
    name='aether-gesture',
    version='3.1.0',
    packages=find_packages(),
    install_requires=[
        'opencv-python>=4.8.0',
        'mediapipe>=0.10.0',
        'numpy>=1.24.0',
        'scikit-learn>=1.3.0',
        'pyautogui>=0.9.54',
    ],
    extras_require={
        'windows': ['pycaw>=20181226', 'comtypes>=1.2.0'],
    },
    entry_points={
        'console_scripts': [
            'aether=main:main',
            'aether-whiteboard=air_whiteboard:main',
        ],
    },
    author='Aether Team',
    description='Production-grade gesture interaction platform with Air Whiteboard.',
    long_description=readme(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=3.8',
)
