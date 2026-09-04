#!/usr/bin/env python3
"""Setup script for attendance bot"""

from setuptools import setup, find_packages

setup(
    name="attendance-bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot==20.8",
        "APScheduler==3.10.4",
        "geopy==2.4.1",
        "sqlalchemy==2.0.23",
        "aiosqlite==0.19.0",
        "asyncpg==0.29.0",
        "python-dotenv==1.0.0",
        "pytz==2023.3",
    ],
    python_requires=">=3.11",
)
