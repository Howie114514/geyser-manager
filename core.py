import configparser,os,json
from pathlib import Path
import requests
import yaml
from yaml import Loader,Dumper
import g_default_config
import threading
import subprocess
from textual.widgets import Log

#path=os.path

config=configparser.ConfigParser()
config_path=str(Path.home())+"/.geyser-manager/config.conf"
server_list_path=str(Path.home())+"/.geyser-manager/servers.json"
geyser_path=str(Path.home())+"/.geyser-manager/geyser"

#Default
config["program"]={
	"initialized":0
}
config["game"]={
	"currentServer":"",
	"protocolVersion":"",
	"mcVersion":""
}

os.makedirs(os.path.dirname(config_path),exist_ok=True)
os.makedirs(geyser_path,exist_ok=True)

def saveConfig():
	with open(config_path,"w") as f:
		config.write(f)

if os.path.isfile(config_path):
	config.read(config_path)
else:
	saveConfig()
		
servers=[]
if os.path.isfile(server_list_path):
	servers=json.load(open(server_list_path))

class GeyserManager:
	def saveServerList(self):
		json.dump(servers,open(server_list_path,"w"))
	def updateVersionData(self):
		p=self.getProtocolVersion(ignoreError=False)
		config["game"]["protocolVersion"]=str(p["id"])
		config["game"]["mcVersion"]=p["name"]
		saveConfig()
	def downloadGeyser(self):
		self.app.notify("下载geyser中...")
		try:
			c=requests.get("https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/standalone").content
			open(os.path.join(geyser_path,"geyser.jar"),"wb").write(c)
			self.app.notify("成功！")
			return True
		except Exception as e:
			self.app.notify("出错了！\n"+str(e),severity="error")
			return False
	def readGeyserConfig(self):
		if os.path.isfile(os.path.join(geyser_path,"config.yml")):
			return yaml.load(open(os.path.join(geyser_path,"config.yml")),Loader=Loader)
		else:
			return yaml.load(g_default_config.content,Loader=Loader)
	def configure(self,d):
		o=self.readGeyserConfig()
		o.update(d)
		yaml.dump(o,open(os.path.join(geyser_path,"config.yml"),"w"),Dumper=Dumper)
	geyser_process=None
	def start(self):
		if self.geyser_process:
			self.geyser_process.kill()
		self.geyser_process=subprocess.Popen(["java","-jar",os.path.join(geyser_path,"geyser.jar")],cwd=geyser_path,stdout=subprocess.PIPE,stdin=subprocess.PIPE)
	def getServerById(self,server):
		r=list(filter(lambda x:x["id"]==server,servers))
		if len(r)==0:
			return None
		return r[0]
	
	def getProtocolVersion(self,ignoreError=True):
		try:
			response = requests.get("https://api.geysermc.org/v2/versions/geyser").json()
			return response["bedrock"]["protocol"]
		except Exception as e:
			self.app.notify("检查更新时发生错误："+str(e))
			if not ignoreError:
				raise e
	def __init__(self,app):
		self.app=app
		