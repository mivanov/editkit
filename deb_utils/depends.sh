#!/bin/bash
# Prints out the package dependencies for a specific Ubuntu release

if [ $# -eq 0 ]
then
  echo "Usage: $0 <ubuntu_release(ex: lucid)>"
  exit 1
fi

depends="python-pip, python-virtualenv, python-setuptools, python-lxml, python-imaging, libapache2-mod-wsgi, git-core, mercurial, subversion"

echo ${depends}
