## pep.py
This is Ripple's bancho server. It handles:
- Client login
- Online users listing and statuses
- Public and private chat
- Spectator
- Multiplayer
- Fokabot

## Requirements
- Python 3.5
- MySQLdb (`mysqlclient`)
- Tornado
- Gevent
- Bcrypt
- Raven

## How to set up pep.py
First of all, install all the dependencies
```
$ pip install -r requirements.txt
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
All code in this repository is licensed under the GNU AGPL 3 License.  
See the "LICENSE" file for more information  
This project contains code taken by reference from [miniircd](https://github.com/jrosdahl/miniircd) by Joel Rosdahl.
