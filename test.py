import core
from textual.app import App

app=App()
m=core.GeyserManager(app)
m.downloadGeyser()