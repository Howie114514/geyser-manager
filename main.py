from textual.app import App
from textual.widgets import Header,Button,Label,Footer,Static,LoadingIndicator,Input,Select,Log,OptionList
from textual.widgets.option_list import Option, Separator
from textual.widget import Widget
from textual.screen import Screen
from textual.containers import Horizontal
import core
import threading
import sys,subprocess
import os.path
import atexit
import re
import random
import uuid

@atexit.register
def on_exit():
	if gm.geyser_process:
		gm.geyser_process.terminate()
		print("已清理Geyser进程")

def startThread(t):
	th=threading.Thread(target=t)
	th.daemon=True
	th.start()
	return th

class CommonScreen(Screen):
	def compose(self):
		yield Header()
		yield Footer(show_command_palette=False)

class WelcomeScreen(CommonScreen):
	def refresh_data(self):
		if core.config["program"]["initialized"]=="1":
			server = gm.getServerById(core.config["game"]["currentServer"])
			if server:
				self.query_one("#cserver").update(content=f"当前服务器：{server["name"]}")
			else:
				self.query_one("#cserver").update(content="当前选中无服务器")
			self.query_one("#geyser_version").update(content=f"Geyser适配版本:{core.config["game"]["mcVersion"]}({core.config["game"]["protocolVersion"]})")
		
	def compose(self):
		yield from super().compose()
		yield Label("⛲Geyser Manager⛲")
		yield Label("--轻松使用基岩版畅玩Java版服务器--")
		if core.config["program"]["initialized"]=="0":
			yield Label("您看上去是第一次使用本软件\n点击'初始化'按钮完成最基本的配置")
			yield Button("▶初始化",variant="primary",id="setup")
		else:
			yield Label("Geyser适配版本:1.21.50(766)",id="geyser_version")
			yield Label("当前服务器：",id="cserver")
			yield Button("🗺管理服务器",id="server_list")
			yield Button("▶启动",id="start")
			yield Button("⚙设置",id="settings")
		yield Button("❔帮助",id="help")
		yield Button("✗ 退出",id="exit")
		if "-debug" in sys.argv:
			yield Button("测试",id="test")
		#yield Log(classes="log")
	def on_screen_resume(self):
		self.refresh_data()
		
class HelpScreen(CommonScreen):
	def compose(self):
		yield from super().compose()
		yield Static("？帮助")
		yield Static("Ctrl+Q可退出应用\n若Termux输入法消失划走重新进入即可恢复")
		yield Button("退出",variant="error",id="exit_scr")
		
class SettingsScreen(CommonScreen):
	settings=[
		{
			"id":"port",
			"key":"bedrock/port",
			"name":"端口",
			"desc":"连接服务器时所用的端口",
			"type":"int",
			"default":19132,
			"get_value":lambda v:int(v)
		},
		{
			"name":"用户名",
			"desc":"填入您的用户名可以避免每次输密码登陆\n您的token将会被保存（请不要向别人发送您的token）\n多个用户名可用';'分隔",
			"type":"str",
			"id":"username",
			"key":"saved-user-logins",
			"default":"",
			"from_file":lambda o:";".join(o),
			"get_value":lambda o:o.split(";")
		},
		{
			"name":"登陆方式",
			"desc":"这将会决定您如何登陆服务器。",
			"type":"select",
			"selections":[("正版登陆",0),("离线登陆",1)],
			"default":0,
			"id":"auth_type",
			"key":"remote/auth-type",
			"from_file":lambda m:["online","offline"].index(m),
			"get_value":lambda m:["online","offline"][m]
		},
		{
			"name":"下界上层建筑",
			"desc":"这将会使您的下界维度ID为变为末地",
			"type":"select",
			"selections":[("开",0),("关",1)],
			"default":0,
			"get_value":lambda o:o==0,
			"id":"above_bedrock_nether_building",
			"key":"above-bedrock-nether-building",
			"from_file":lambda m:int(not m)
		}
	]

	def save(self):
		obj = gm.readGeyserConfig()
		for s in self.settings:
			okeypath=s["key"].split("/")
			keypath=s["key"].split("/")
			keypath.pop()
			o=obj
			for k in keypath:
				o=o[k]
			#o[okeypath[-1]] = ""
			v=app.query_one(f"#{s['id']}").value
			if not v and "default" in s:
				v=s["default"]
			if "get_value" in s:
				v=s["get_value"](v)
			o[okeypath[-1]]=v
		gm.configure(obj)
			
	def composeSettings(self,settings,o):
		for s in self.settings:
			yield Label(s["name"])
			yield Label(s["desc"],classes="desc")
			keypath=s["key"].split("/")
			r=o
			for k in keypath:
				try:
					r=r[k]
				except:
					r=None
			
			if r==None:
				if "default" in s:
					r=s["default"]
			else:
				if "from_file" in s:
					r=s["from_file"](r)
			match(s["type"]):
				case "int":
					yield Input(type="integer",id=s["id"],value=str(r))
				case "str":
					yield Input(id=s["id"],value=str(r))
				case "select":
					yield Select(s["selections"],id=s["id"],allow_blank=False,value=r)
	def compose(self):
		yield from super().compose()
		geyser_config=gm.readGeyserConfig()
		yield from self.composeSettings(self.settings,geyser_config)
		yield Button("保存",id="save_settings")
		yield Button("取消",id="exit_scr")
	def on_button_pressed(self,event):
		if event.button.id=="save_settings":
			self.save()
			app.pop_screen()
		
class LoadingScreen(CommonScreen):
	def compose(self):
		yield from super().compose()
		yield LoadingIndicator()
		
class MessageScreen(Screen):
	title="提示"
	content="内容"
	ltitle=Label(title,classes="title")
	lcontent=Label(content,classes="content")	
	
	def compose(self):
		yield self.ltitle
		yield self.lcontent
		yield Button("退出",id="exit_scr")
		
imsg=MessageScreen()

class ServerList(CommonScreen):
	def __init__(self, name = None, id = None, classes = None):
		super().__init__(name, id, classes)
	def generateOptions(self):
		r = []
		for s in core.servers:
			r.append(Option(f"{s['name']}"))
		return r
	def refresh_list(self):
		try:
			self.servers.clear_options()
			self.servers.add_options(self.generateOptions())
			if self.servers.highlighted==None:
				for e in self.query(".server_list_btn"):
					e.disabled=True
			index = self.indexById(core.config["game"]["currentServer"])
			self.servers.highlighted = index
		except:
			pass

	def on_mount(self):
		self.refresh_list()
		
	def compose(self):
		yield Label("服务器列表",classes="title")
		self.servers = OptionList(*self.generateOptions())
		yield self.servers
		yield Button("编辑",id="edit",classes="server_list_btn")
		yield Button("使用",id="use",classes="server_list_btn")
		yield Button("删除",id="remove",classes="server_list_btn")
		yield Button("添加",id="add")
		yield Button("退出",variant="error",id="exit_scr")

	def removeServer(self):
		index = self.servers.highlighted
		if not index==None:
			core.servers.pop(index)
			gm.saveServerList()
			self.refresh_list()
	
	def editServer(self):
		index = self.servers.highlighted
		if not index==None:
			info = core.servers[index]
			app.edit_server_screen.info = info
			app.edit_server_screen.index = index
			app.edit_server_screen.is_new_server = False
		app.push_screen("edit_server")

	def indexById(self,id):
		i=0
		for s in core.servers:
			if s["id"]==id:
				return i
			i+=1

	def addServer(self):
		app.edit_server_screen.info = {
			"name":"Java版服务器"+str(len(core.servers)+1),
			"addr":"",
			"id":str(uuid.uuid4())
		}
		app.edit_server_screen.index = None
		app.edit_server_screen.is_new_server = True
		app.push_screen("edit_server")

	def on_screen_resume(self):
		self.refresh_list()

	def on_button_pressed(self,event):
		match event.button.id:
			case "add":
				self.addServer()
			case "edit":
				self.editServer()
			case "remove":
				self.removeServer()
			case "use":
				self.useServer()

	def useServer(self):
		index = self.servers.highlighted
		if not index==None:
			info = core.servers[index]
			config = gm.readGeyserConfig()
			config["bedrock"]["motd1"] = info["name"]
			address = info["addr"].split(":")
			ip=""
			port=""
			if len(address)==2:
				ip,port = address
			else:
				ip=address
			config["remote"]["address"]=ip
			if not port=="":
				config["remote"]["port"]=int(port)
			core.config["game"]["currentServer"]=info["id"]
			core.saveConfig()
			app.notify("服务器已切换为"+info["name"]+f"\n[{info['addr']}]")

	def on_option_list_option_highlighted(self,event):
		if not self.servers.highlighted==None:
			for e in self.query(".server_list_btn"):
				e.disabled=False

class EditServerScreen(CommonScreen):
	info={
		"name":"New Server",
		"addr":"example.com:25565"
	}
	index=None
	is_new_server=False
	def on_screen_resume(self):
		app.query_one("#name_input").value=self.info["name"]
		app.query_one("#addr_input").value=self.info["addr"]
	def compose(self):
		yield from super().compose()
		yield Label("编辑服务器")
		yield Label("名字")
		yield Input(id="name_input")
		yield Label("地址(<IP>[:端口])")
		yield Input(id="addr_input")
		yield Button("确认",id="edit_server_confirm")
		yield Button("退出",variant="error",id="exit_scr")
	def on_button_pressed(self,event):
		if event.button.id=="edit_server_confirm":
			self.info["name"] = app.query_one("#name_input").value
			addr = app.query_one("#addr_input").value
			if not re.match(r"^((([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+)|localhost)(\:[0-9]+)?$",addr):
				app.notify("服务器地址格式不正确！",severity="error")
				return
			self.info["addr"]=addr
			if self.is_new_server:
				core.servers.append(self.info)
				self.index = len(core.servers)-1
			else:
				core.servers[self.index] = self.info
			gm.saveServerList()
			app.pop_screen()
			app.server_list_screen.refresh_list()
			app.server_list_screen.servers.highlighted = self.index

class TextUIApp(App):
	CSS_PATH="style.tcss"
	SCREENS={"help":HelpScreen,"loading":LoadingScreen,"settings":SettingsScreen}
	def __init__(self):
		super().__init__()
		self.install_screen(imsg,"msg")
		self.edit_server_screen = EditServerScreen()
		self.install_screen(self.edit_server_screen,"edit_server")
		self.server_list_screen=ServerList()
		self.install_screen(self.server_list_screen,"server_list")
		self.welcome_screen=WelcomeScreen()
		self.install_screen(self.welcome_screen,"welcome")
	def on_mount(self):
		self.push_screen("welcome")
		self.title="Geyser Manager"
	def showLoadingScreen(self):
		self.push_screen("loading")
	def setup(self):
		self.notify("正在初始化中，请不要操作。")
		r="-dev-no-download" in sys.argv or gm.downloadGeyser()
		if r:
			gm.configure({"saved-user-logins":[]})
			gm.updateVersionData()
			self.notify("初始化成功完成！",timeout=114514)
			core.config["program"]["initialized"]="1"
			core.saveConfig()
		else:
			self.notify("初始化失败！请检查您的网络连接并重试！",timeout=114514)
		#self.pop_screen()
	def waitForExit(self):
		gm.geyser_process.wait()
		self.notify(f"[返回值：{gm.geyser_process.returncode}]",title="Geyser已退出")
		gm.geyser_process=None
		sb=self.query_one("#start")
		sb.label="▶启动"
		sb.variant="default"
	def on_button_pressed(self,event):
		match event.button.id:
			case "setup":
				self.showLoadingScreen()
				startThread(self.setup)
				#self.setup()
			case "help":
				self.push_screen("help")
			case "exit_scr":
				self.pop_screen()
			case "settings":
				self.push_screen("settings")
			case "exit":
				self.exit()
			case "start":
				if not gm.geyser_process:
					if gm.getServerById(core.config["game"]["currentServer"]):
						gm.start()
						sb=self.query_one("#start")
						sb.label="✗停止"
						sb.variant="error"
						startThread(self.waitForExit)
					else:
						self.notify("当前无选中服务器，请点击“管理服务器”并选中或添加服务器。")
				else:
					gm.geyser_process.terminate()
					sb=self.query_one("#start")
					sb.label="▶启动"
					sb.variant="default"
			case "server_list":
				self.push_screen("server_list")
					

if __name__ == "__main__":
	app = TextUIApp()
	gm=core.GeyserManager(app)
	app.run()