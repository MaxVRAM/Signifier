import json

CONFIG_FILE = 'config.json'

with open(CONFIG_FILE) as c:
    config = json.load(c)

for name in config.keys():
    if 'clip' in name:
        print(name)