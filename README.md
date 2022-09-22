# ska-rucio-extended-client

## Install

### Local development via pip w/ symlinks

Development inside container, e.g.:

```bash
eng@ubuntu:~$ docker run -it -v ~/SKAO/ska-rucio-extended-client:/home/user/ska-rucio-extended-client registry.gitlab.com/ska-telescope/src/ska-rucio-client:release-1.29.
[user@af38271f5e57 ~]$ sed -c -i "s/\(account *= *\).*/\1robbarnsley/" /opt/rucio/etc/rucio.cfg
[user@af38271f5e57 ~]$ rucio whoami
[user@af38271f5e57 ~]$ cd ska-rucio-extended-client/
[user@af38271f5e57 ska-rucio-extended-client]$ python3 -m pip install -e .
[user@af38271f5e57  bin]$ python3 rucio-upload-directory --rse STFC_STORM --scope hierarchy_tests -d ../test -c ../etc/config.ini -n test
```

## Functions

- rucio-upload-directory: upload a multi-level directory