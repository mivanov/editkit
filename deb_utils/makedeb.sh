#!/bin/bash
# Used for local testing only!
# Builds a binary .deb with suite set to "unstable"

cd ..
LW_VERSION=$(python -c "from editkit import get_version; print get_version().replace(' ', '.')")

DEPENDS=$(deb_utils/depends.sh lucid)

rm -r deb_dist/
rm -r editkit.egg-info/

python setup.py --command-packages=stdeb.command sdist_dsc --ignore-install-requires --suite unstable --depends "${DEPENDS}"

cp deb_utils/editkit.postinst deb_dist/editkit-${LW_VERSION}/debian
cp deb_utils/triggers deb_dist/editkit-${LW_VERSION}/debian
cd deb_dist/editkit-${LW_VERSION}

dpkg-buildpackage -rfakeroot -uc -us
cd ../../deb_utils
