# pep.py
## Ripple's bancho server
This is Ripple's bancho server. It handles:
- Client login
- Online users listing and statuses
- Public and private chat
- Spectator
- Multiplayer
- Fokabot

## Requirements
- Python 3.5
- MySQLdb (`pip install mysqlclient` or `pip install mysql-python`)
- Tornado (`pip install tornado`)
- Bcrypt (`pip install bcrypt`)

## How to set up pep.py
First of all, install all the dependencies
```
$ pip install mysqlclient
$ pip install tornado
$ pip install bcrypt
```
then, run pep.py once to create the default config file and edit it
```
$ python3 pep.py
$ nano config.ini
```
you can run pep.py by typing
```
$ python3 pep.py
```

## License

```
Copyright (C) The Ripple Developers - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential
```
