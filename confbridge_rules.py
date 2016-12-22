'''
THIS EXAMPLE WILL NOT WORK AS IT IS - YOU MUST SPECIFY YOUR OWN VALUES!!!


'''

BRIDGES = {
    'KANSAS': [
            {'SYSTEM': 'LAWRENCE',     'TS': 2, 'TGID': 3120,  'ACTIVE': True, 'TIMEOUT': 2, 'TO_TYPE': 'ON',  'ON': [2,], 'OFF': [9,]},
            {'SYSTEM': 'C-BRIDGE',     'TS': 2, 'TGID': 3120,  'ACTIVE': True, 'TIMEOUT': 2, 'TO_TYPE': 'OFF',  'ON': [2,], 'OFF': [9,]},
            {'SYSTEM': 'BRANDMEISTER', 'TS': 2, 'TGID': 3120,  'ACTIVE': True, 'TIMEOUT': 2, 'TO_TYPE': 'NONE',  'ON': [2,], 'OFF': [9,]},
        ],
    'BYRG': [
            {'SYSTEM': 'LAWRENCE',     'TS': 1, 'TGID': 3100,  'ACTIVE': True, 'TIMEOUT': 2, 'TO_TYPE': 'NONE', 'ON': [3,], 'OFF': [8,]},
            {'SYSTEM': 'BRANDMEISTER', 'TS': 2, 'TGID': 31201, 'ACTIVE': True, 'TIMEOUT': 2, 'TO_TYPE': 'NONE', 'ON': [3,], 'OFF': [8,]},
        ],
    'ENGLISH': [
            #{'SYSTEM': 'LAWRENCE', 'TS': 1, 'TGID': 13,    'ACTIVE': True, 'TIMEOUT': 2, 'TO_TYPE': 'NONE', 'ON': [4,], 'OFF': [7,]},
            {'SYSTEM': 'C-BRIDGE', 'TS': 1, 'TGID': 13,    'ACTIVE': True, 'TIMEOUT': 2, 'TO_TYPE': 'NONE', 'ON': [4,], 'OFF': [7,]},
        ]
}

if __name__ == '__main__':
    from pprint import pprint
    pprint(BRIDGES)