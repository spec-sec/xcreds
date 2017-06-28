echo -e "\nInstalling prerequisites for xcreds...\n"

# dnsmasq, hostapd

apt-get update

if [[ $(which dnsmasq) ]]; then
    echo -e "\nDnsmasq already installed!"
else
    echo -e "\nInstalling dnsmasq..."
    apt-get install dnsmasq -y
fi

if [[ $(which hostapd) ]]; then
    echo -e "\nHostapd already installed!"
else
    echo -e "\nInstalling hostapd..."
    apt-get install hostapd -y
fi

if [[ $(python -c 'import pkgutil; print(1 if pkgutil.find_loader("web") else 0)') == 1 ]]; then
    echo -e "\nWeb.py already installed!"
else
    echo -e "\nInstalling web.py..."
    pip install web.py
fi

echo -e "\nInstall Complete!\n"


