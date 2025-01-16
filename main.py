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
	def compose(self):
		yield from super().compose()
		yield Label("⛲Geyser Manager⛲")
		yield Label("--轻松使用基岩版畅玩Java版服务器--")
		if core.config["program"]["initialized"]=="0":
			yield Label("您看上去是第一次使用本软件\n点击'初始化'按钮完成最基本的配置")
			yield Button("▶初始化",variant="primary",id="setup")
		else:
			yield Button("🗺管理服务器",id="server_list")
			yield Button("▶启动",id="start")
			yield Button("⚙设置",id="settings")
		yield Button("❔帮助",id="help")
		yield Button("✗ 退出",id="exit")
		if "-debug" in sys.argv:
			yield Button("测试",id="test")
		#yield Log(classes="log")
		
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
			"key":"port",
			"name":"端口",
			"desc":"连接服务器时所用的端口",
			"type":"int",
			"default":19132
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
			"get_value":lambda o:["online","offline"][o],
			"id":"auth_type",
			"key":"remote/auth_type",
			"from_file":lambda m:["online","offline"].index(m),
			"get_value":lambda m:["online","offline"][m]
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
	def compose(self):
		yield Label("服务器列表",classes="title")
		self.servers = OptionList(*self.generateOptions())
		yield self.servers
		yield Button("编辑",id="edit",classes="server_list_btn")
		yield Button("使用",id="use",classes="server_list_btn")
		yield Button("添加",id="add")
		yield Button("退出",variant="error",id="exit_scr")

	def on_mount(self):
		for e in self.query(".server_list_btn"):
			e.disabled=True

	def on_button_pressed(self,event):
		match event.button.id:
			case "add":
				app.push_screen("edit_server")

class EditServerScreen(CommonScreen):
	server_index=0
	def compose(self):
		yield from super().compose()
		yield Label("编辑服务器")
		yield Label("名字")
		yield Input()
		yield Label("地址(<IP>[:端口])")
		yield Input()
		yield Button("确认",id="add_server")
		yield Button("退出",variant="error",id="exit_scr")
		

class TextUIApp(App):
	CSS_PATH="style.tcss"
	SCREENS={"welcome":WelcomeScreen,"help":HelpScreen,"loading":LoadingScreen,"settings":SettingsScreen,"server_list":ServerList}
	def __init__(self):
		super().__init__()
		self.install_screen(imsg,"msg")
		self.edit_server_screen = EditServerScreen()
		self.install_screen(self.edit_server_screen,"edit_server")
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
			self.notify("初始化成功完成！现在您可以按下Ctrl+Q退出然后重启本软件",timeout=114514)
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
					gm.start()
					sb=self.query_one("#start")
					sb.label="✗停止"
					sb.variant="error"
					startThread(self.waitForExit)
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