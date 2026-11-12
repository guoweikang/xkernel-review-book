#!/bin/bash
set -euo pipefail
if [ "$#" -lt 4 ] || [ "$(readlink /proc/self/ns/user)" = "$(readlink /proc/1/ns/user)" ]; then
    echo 'Run only inside a fresh unshare user/mount/PID/network namespace.' >&2
    exit 2
fi
root=$1
work=$2
tools=$3
shift 3
for path in "$root" "$work" "$tools"; do
    [[ "$path" = /* ]] || exit 2
done
[[ ! -e "$root" && -d "$work" && -d "$tools" ]] || exit 2
mount --make-rprivate /
mkdir -p "$root"/{usr,work,tools,proc,dev,tmp,etc}
ln -s usr/bin "$root/bin"
ln -s usr/lib "$root/lib"
ln -s usr/lib64 "$root/lib64"
mount --bind /usr "$root/usr"
mount -o remount,bind,ro "$root/usr"
mount --bind "$tools" "$root/tools"
mount -o remount,bind,ro "$root/tools"
mount --bind "$work" "$root/work"
mount -t tmpfs -o size=128m,nosuid,nodev tmpfs "$root/tmp"
mkdir -p "$root/dev/shm"
mount -t tmpfs -o size=64m,nosuid,nodev tmpfs "$root/dev/shm"
for device in null zero random urandom; do
    touch "$root/dev/$device"
    mount --bind "/dev/$device" "$root/dev/$device"
done
ulimit -c 0
ulimit -v 3145728
ulimit -t 120
exec chroot "$root" /usr/bin/setpriv --bounding-set=-all --inh-caps=-all --no-new-privs \
    /usr/bin/env -i HOME=/tmp LANG=C.UTF-8 \
    JAVA_HOME=/tools/jdk8u504-b01 ANT_HOME=/tools/apache-ant-1.10.18 \
    LD_LIBRARY_PATH=/tools/jdk8u504-b01/jre/lib/amd64/jli:/tools/jdk8u504-b01/jre/lib/amd64:/tools/jdk8u504-b01/jre/lib/amd64/server \
    JAVA_TOOL_OPTIONS='-Xms64m -Xmx512m -XX:+UseSerialGC -XX:MaxMetaspaceSize=128m -XX:CompressedClassSpaceSize=128m' \
    PATH=/tools/jdk8u504-b01/bin:/tools/apache-ant-1.10.18/bin:/work/bin:/usr/bin \
    ANT_OPTS='-Xms64m -Xmx256m -XX:MaxMetaspaceSize=128m -XX:CompressedClassSpaceSize=128m' \
    "$@"
