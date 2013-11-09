# Copyright (c) 2013 Cortney T. Buffington, N0MJS and the K0USY Group. n0mjs@me.com
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# Logging system configuration

from logging.config import dictConfig
import logging

# Full path/name of the log file:
_log_file_name = '/tmp/dmrlink.log'

dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'timed': {
            'format': '%(levelname)s %(asctime)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'console-timed': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'timed'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'simple',
            'filename': _log_file_name,
        },
        'file-timed': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'timed',
            'filename': _log_file_name,
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'dmrlink': {
            'handlers': ['file-timed', 'syslog'],
#            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        }
    }
})
logger = logging.getLogger('dmrlink')
