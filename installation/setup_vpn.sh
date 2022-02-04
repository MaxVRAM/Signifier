#!/bin/sh
apt update
apt upgrade -y
apt install openvpn -y
mkdir -p /etc/openvpn/client
chown root:root /etc/openvpn/client
chmod 700 /etc/openvpn/client
chown root:root client.ovpn
chmod 700 client.ovpn
mv client.ovpn /etc/openvpn/client
openvpn --config /etc/openvpn/client/client.ovpn --daemon
cp /etc/openvpn/client/client.ovpn /etc/openvpn/client.conf
systemctl enable openvpn@client.service
systemctl start openvpn@client.service