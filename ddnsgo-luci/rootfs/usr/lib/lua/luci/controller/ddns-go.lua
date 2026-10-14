-- DDNS-GO LuCI 入口 (为 flippy/LEDE 老式 LuCI 编写)
-- 官方 luci-app-ddns-go 用 menu.d/*.json + resources/view/*.js，
-- 本固件的 createindex() 只扫 /usr/lib/lua/luci/controller/*.lua，不读 menu.d，
-- dispatcher.lua 里也没有 view() 函数 → 官方菜单在此固件上天生不出现。
-- 这里用本固件支持的老式写法补一个入口，页面内嵌 ddns-go 自带 Web UI。
module("luci.controller.ddns-go", package.seeall)

function index()
	entry({"admin", "services", "ddns-go"},
		alias("admin", "services", "ddns-go", "ddns-go"),
		_("DDNS-GO"), 58)

	entry({"admin", "services", "ddns-go", "ddns-go"},
		template("ddns-go/ddns-go"),
		_("DDNS-GO"), 1).leaf = true
end
