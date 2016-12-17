## pep.py [![Code Health](https://landscape.io/github/osuripple/pep.py/master/landscape.svg?style=flat)](https://landscape.io/github/osuripple/pep.py/master)

- Origin: https://git.zxq.co/ripple/pep.py
- Mirror: https://github.com/osuripple/pep.py

This is Ripple's bancho server. It handles:
- Client login
- Online users listing and statuses
- Public and private chat
- Spectator
- Multiplayer
- Fokabot

## Requirements
- Python 3.5
- Cython
- C compiler
- MySQLdb (`mysqlclient`)
- Tornado
- Bcrypt
- Raven

## How to set up pep.py
First of all, initialize and update the submodules
```
$ git submodule init && git submodule update
```
afterwards, install the required dependencies with pip
```
$ pip install -r requirements.txt
```
then, compile all `*.pyx` files to `*.so` or `*.dll` files using `setup.py` (distutils file)
```
$ python3 setup.py build_ext --inplace
```
finally, run pep.py once to create the default config file and edit it
```
$ python3 pep.py
...
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
