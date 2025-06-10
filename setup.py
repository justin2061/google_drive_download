from distutils.core import setup
import py2exe
from base64 import encode
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import io
import os
import pickle
import sys, getopt
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
import traceback
import json
import re

data_files = []
setup(
    console=['download.py'],
    options={
        'py2exe':{
            'packages':[''],
            'dist_dir': 'dist',
            'compressed': True,
            'includes': ['paramiko', 'MySQLdb']
        }
    },
    data_files=data_files 
    )