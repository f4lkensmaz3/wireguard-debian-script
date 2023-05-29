#!/usr/bin/python

import os
import sys
import requests

def main():
    # -- ENV CHECK
    f_qr = False
    if os.geteuid() != 0:
        exit('Please be root')
    if '-q' in sys.argv:
        import pyqrcode
        f_qr = True
    # --

    os.system("sudo apt-get update -y && sudo apt-get upgrade -y && sudo apt-get install wireguard iptables ufw -y") # INSTALLING REQUIREMENTS
    os.system("umask 077; wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey")    # KEY GENERATION FOR SERVER
    os.system('wg genkey | tee clientprivate | wg pubkey > clientpublic')       # KEY GENERATION FOR CLIENT

    with open('/etc/wireguard/privatekey','r') as f:   # READ KEYS FOR SERVER CONFIG
        spv = f.read().strip()
        f.close()
    with open('clientpublic','r') as f:         # READ KEYS FOR SERVER CONFIG
        cpb = f.read().strip()
        f.close()
    with open('/etc/wireguard/wg0.conf','a+') as f:     # CREATE CONFIG
        f.write(f'[Interface]\nAddress = 192.168.10.1/24\nSaveConfig = true\nPostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE\nPostUp = ufw route allow in on wg0 out on eth0\nPostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE\nPostDown = ufw route delete allow in on wg0 out on eth0\nListenPort=51194\nPrivateKey = {spv}\n[Peer]\nPublicKey = {cpb}\nAllowedIPs = 192.168.10.2/32')
        f.close()

    # SET OTHER CONFIGS. SET FIREWALL
    os.system('echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf')
    os.system('sudo sysctl -p && sudo systemctl enable wg-quick@wg0 && sudo systemctl start wg-quick@wg0')      # ENABLE WIREGUARD SERVER
    os.system('ufw default deny incoming & ufw default allow outgoing')     # FIREWALL SETTINGS
    os.system('ufw allow ssh')
    os.system('ufw allow 51194/udp')

    # -- INSTALL ENCRYPTED DNS
    os.system('wget https://github.com/AdguardTeam/dnsproxy/releases/download/v0.49.1/dnsproxy-linux-amd64-v0.49.1.tar.gz -P /tmp/')    # DOWNLOAD ADGUARD DNSPROXY
    os.system('tar -xf /tmp/dnsproxy-linux-amd64-v0.49.1.tar.gz -C /tmp/ && mv /tmp/linux-amd64/dnsproxy /usr/sbin/ && rm -r /tmp/dnsproxy-linux-amd64-v0.49.1.tar.gz /tmp/linux-amd64') # INSTALL DNSPROXY

    with open ('/etc/systemd/system/ad-dnsproxy.service','w+') as f: # CREATE A SERVICE FILE
        f.write("[Unit]\nDescription=ad-dnsproxy\nAfter=network.target\n\n[Service]\nExecStart=/usr/sbin/dnsproxy -u 'https://dns.quad9.net/dns-query' -b 9.9.9.9\nType=simple\nRestart=always\n\n[Install]\nWantedBy=default.target\nRequiredBy=network.target")
        f.close()
    os.system('systemctl daemon-reload && systemctl enable ad-dnsproxy && systemctl start ad-dnsproxy')     # ENABLE DNSPROXY
    os.system('echo nameserver 127.0.0.1 > /etc/resolv.conf')   # EDIT RESOLVCONF
    os.system('ufw allow from any to 192.168.10.1 port 53')     # ALLOW DNS PORT FOR wg0(VPN NETWORK)
    os.system('echo y | ufw enable')                            # ENABLE UFW

    with open('/etc/wireguard/publickey','r') as f:
        spb = f.read().strip()
        f.close()
    with open('clientprivate','r') as f:
        cpv = f.read().strip()

    ip = requests.get('https://ipv4.icanhazip.com').text.strip()

    with open('wg0.conf','w+') as f:
        config = f'[Interface]\nPrivateKey = {cpv}\nAddress = 192.168.10.2/24\nDNS = 192.168.10.1\n\n[Peer]\nPublicKey = {spb}\nAllowedIPs = 0.0.0.0/0\nEndpoint = {ip}:51194\nPersistentKeepalive = 20'
        f.write(config)
    print('Config file created in "wg0.conf"')
    if f_qr:
        qr = pyqrcode.create(config)
        qr.png('qr.png',scale=5)
        print(qr.terminal())


if __name__ == '__main__':
    main()
