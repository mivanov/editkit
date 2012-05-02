#!/bin/bash
# Makes deb source for a given Ubuntu release using prebuilt source
# and uploads it to the specified PPA

if [[ "$1" = "" ]] || [[ "$2" = "" ]] || [[ "$3" = "" ]]
then
  echo "Usage: $0 <ubuntu_release(ex: lucid)> <prebuilt_dist.orig.tar.gz> <user/ppa>"
  exit
fi

cd ..
LW_VERSION=$(python -c "from editkit import get_version; print get_version().replace(' ', '.')")
UBUNTU_RELEASE=$1
DEBIAN_VERSION="0ubuntu1~${UBUNTU_RELEASE}"
DIST_FILE=$2
PPA=$3
VERSION="${LW_VERSION}-${DEBIAN_VERSION}"
DEPENDS=$(deb_utils/depends.sh ${UBUNTU_RELEASE})

echo "Building package source for editkit_${VERSION}"

rm -r deb_dist/
rm -r editkit.egg-info/

python setup.py --command-packages=stdeb.command sdist_dsc --ignore-install-requires --suite ${UBUNTU_RELEASE} --debian-version ${DEBIAN_VERSION}  --depends "${DEPENDS}" --use-premade-distfile ${DIST_FILE}

cp deb_utils/editkit.postinst deb_dist/editkit-${LW_VERSION}/debian
cp deb_utils/triggers deb_dist/editkit-${LW_VERSION}/debian
cd deb_dist/editkit-${LW_VERSION}

dpkg-buildpackage -rfakeroot -S -sa

cd ../
dput ppa:${PPA} editkit_${VERSION}_source.changes
cd ../deb_utils
