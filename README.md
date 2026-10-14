# OpenWrt 固件打包（N1 + X96Max+）· 自包含可 DIY

给 **斐讯 N1** 和 **X96Max+ / HK1 / H96 Max X3 / TX3** 打包 OpenWrt 固件。

## 特点：零外部依赖，可自行修改

普通做法每次打包都要去 GitHub 现clone 别人的仓库——**一旦对方项目挂了，打包立刻失效**。

本仓库把打包所需的脚本与资源**全部本地化**：

```
flippy-vendor/
├── openwrt_flippy.sh          ← 打包主脚本（720 行，可改）
└── openwrt_packit/            ← 打包实现（files/ 94MB，含 u-boot 等）
    └── files/
        ├── firmware/          ← 各机型引导固件
        ├── bootfiles/
        ├── amlogic_model_database.txt
        └── ...各类补丁与工具
```

只保留**内核**依赖 `ophub/kernel`（这是唯一必须在线的部分）。

---

## 使用方法

仓库里有两个打包 workflow，按需要选一个：

| Workflow | 产出 Release tag | 内容 |
|---|---|---|
| `Package N1 & X96Max+ (self-contained)` | `N1-X96MaxPlus` | **纯净版**：F大官方 rootfs + 内核，不注入任何东西 |
| `Package N1 & X96Max+ (with iStore + DDNS-GO)` | `N1-X96MaxPlus-iStore` | **定制版**：在纯净版基础上注入 iStore + 菜单图标修复 + DDNS-GO 的 LuCI 入口 |

### 方式一：在线打包（默认）

1. 打开仓库的 **Actions**，选中你要的 workflow
2. 点 **Run workflow**，参数保持默认即可
3. 等待约 5~10 分钟
4. 到 **Releases** 下载对应 tag 的固件

### 方式二：完全离线打包（长期可用）

先把你自己的 rootfs 上传到本仓库的 Releases，tag 设为 `ROOTFS`，然后触发
`self-contained` workflow，在 `rootfs_file` 填那个资产文件名
（如 `openwrt-armsr-armv8-generic-rootfs.tar.gz`）：

1. 此时**不再访问 ophub**，只依赖你上传的 rootfs + 自己的脚本

> 这样即使 F大（ophub/unifreq）全部下架，本仓库仍可正常打包。

---

## 定制版固件里注入了什么

`Package N1 & X96Max+ (with iStore + DDNS-GO)` 会在 rootfs 里注入三项定制，
**刷完即用，不需要任何手工操作**：

| # | 定制项 | 做法 | 相关文件 |
|---|---|---|---|
| ① | **iStore 应用商店** | 加源 + 把 6 个官方 ipk 预置到 `/usr/share/istore-bootstrap/`，**首次开机由系统自带 opkg 真正安装** | `05-istore-bootstrap` |
| ② | **iStore 菜单图标** | ifit 主题的侧边栏图标是按 `data-title` 硬编码在 `style.css` 里的，iStore 是全菜单唯一"无子菜单的顶层项"，不在表里 → 追加一段补丁（图标取 icomoon `\e903`） | `96-istore-menu-icon` |
| ③ | **DDNS-GO 的 LuCI 菜单** | rootfs 里 `ddns-go` + `luci-app-ddns-go` 其实都装好了，但官方用 `menu.d/*.json + resources/view/*.js` 新架构，本固件的老式 LuCI 认不了 → 补一个老式 controller + 内嵌 WebUI(:9876) 的 view，并打开 `enabled` | `ddnsgo-luci/` |

> ⚠️ **①为什么必须"预置 ipk + 首启用 opkg 装"，而不是直接解包铺文件？**
> 解包铺文件会**绕过 opkg**，导致：包不进 opkg 数据库（iStore 自升级检测失败）、
> `Alternatives` 不处理（`coreutils-stty` 的 `/bin/stty` 是 opkg 现建的软链，铺不出来）、
> 依赖缺失（`taskd` 缺 `script-utils` → 执行 `exec script` 报 not found → 点安装 exit 127 秒失败）。

> ⚠️ **行尾必须是 LF**：`istore-bootstrap/`、`ddnsgo-luci/` 下的脚本都没有扩展名，
> 一旦被写成 CRLF，`#!/bin/sh\r` 在路由器上会直接报 not found，首启钩子整段失效。
> 已在 `.gitattributes` 里强制 `eol=lf`，workflow 里还加了 `sed -i 's/\r$//'` 兜底。

---

## 可 DIY 的地方

| 想改什么 | 改哪里 |
|---|---|
| 打包逻辑（如加机型、改分区） | `flippy-vendor/openwrt_flippy.sh` |
| 引导固件 / 补丁 / 工具 | `flippy-vendor/openwrt_packit/files/` |
| 默认 LAN IP | workflow 参数 `openwrt_ip` |
| 支持的机型 | workflow 参数 `PACKAGE_SOC` |
| 内核版本 | workflow 参数 `kernel_version` |
| 镜像压缩 | workflow 参数 `gzip_imgs` |
| iStore 菜单位置（顶层 / 挪到"系统"下） | workflow 参数 `istore_menu` |
| iStore 首启安装钩子 | `istore-bootstrap/05-istore-bootstrap` |
| ifit 主题的 iStore 图标/颜色 | `istore-bootstrap/96-istore-menu-icon`（`content:"\e903"` / `color:#26C6DA`） |
| DDNS-GO 的菜单入口与页面 | `ddnsgo-luci/rootfs/usr/lib/lua/luci/...` |
| DDNS-GO 的启用钩子 | `ddnsgo-luci/zz-ddnsgo-luci` |

改完直接重新触发 workflow 即可生效。

---

## 产物说明

一次打包产出**两个机型**的固件：

| 文件名 | 对应机型 |
|---|---|
| `openwrt_s905d_n1_*.img.gz` | 斐讯 N1 |
| `openwrt_s905x3_multi_*.img.gz` | X96Max+ / HK1 / H96 Max X3 / TX3 |

刷机方式：U 盘启动 → 系统 → 晶晨宝盒 → 安装 OpenWrt → 选择对应 img

---

## 定制版注入了什么（`N1-X96MaxPlus-iStore`）

| # | 项目 | 注入位置 | 说明 |
|---|---|---|---|
| A | iStore 应用商店 | `/usr/share/istore-bootstrap/` + `/etc/uci-defaults/05-istore-bootstrap` | 6 个 ipk 离线预置，首启用目标系统自带的 opkg 真正安装（**不能直接铺文件**，否则包不登记、软链丢失） |
| B | iStore 侧边栏图标 | `/etc/uci-defaults/96-istore-menu-icon` | ifit 主题只给"有子菜单"的顶层项硬编码了图标；iStore 是唯一的裸 `<li>`，所以补 3 条 CSS |
| C | DDNS-GO 的 LuCI 入口 | `ddnsgo-luci/` + `/etc/uci-defaults/zz-ddnsgo-luci` | 官方包用 `menu.d` 新架构，本固件的 `createindex()` 只扫 `controller/*.lua`，菜单天生不出现 |
| D | **无线路径自愈** | `/etc/hotplug.d/ieee80211/05-wifi-path-fix` | 见下 |
| E | **ifit 样式表版本后缀** | `/etc/uci-defaults/98-ifit-css-cachebust` | 见下 |

### D. 无线路径自愈（内核 6.x 的坑）

内核把 Amlogic mmc 控制器的 sysfs 名改过：

```
6.1.x : platform/soc/ffe03000.sd/mmc_host/...      （.sd）
6.18.x: platform/soc/ffe03000.mmc/mmc_host/...     （.mmc）
```

如果 `/etc/config/wireless` 是从旧系统带过来的（恢复配置备份），里面写死的老路径在新内核上
**永远匹配不到 phy** → `radioN` 报 `"up": false, "retry_setup_failed": true`；
同时 `/etc/hotplug.d/ieee80211/10-wifi-detect` 会以为"这颗 phy 没人认领"，自动补一条
**`LEDE` 开放网络**顶上来 —— 用户看到的现象就是"我的 WiFi 不见了，多了个不认识的网络"。

钩子做两件事：把 `ffeXXXXX.sd/` 批量改成 `ffeXXXXX.mmc/`；`radio1` 与 `radio0` 路径相同时删掉 `radio1`。

> 为什么用 `hotplug.d` 而不是 `uci-defaults`：`uci-defaults` 在 `/etc/init.d/boot` 里执行得太早，
> 那时 SDIO 网卡还没枚举完、`/etc/config/wireless` 往往还不存在。`05-` 前缀保证它排在
> `10-wifi-detect` 之前，先修好路径再让 detect 判重，就不会多补一个 radio。

### E. 样式表版本后缀

uhttpd 只发 `ETag` / `Last-Modified`，**不发 `Cache-Control` / `Expires`**。按 RFC 7234 §4.2.2，
浏览器会对这类响应做"启发式缓存"，有效期约 `(缓存时刻 − Last-Modified) × 10%`。
老 `style.css` 的 `Last-Modified` 是出厂日期，缓存一次能"新鲜"几十天，**期间根本不回服务器验证** ——
于是补丁明明生效了，用户看到的还是旧界面。

钩子给 `header.htm` 里的 `<link ... style.css>` 加上 `?v=<css 的 mtime>`，URL 一变浏览器必然重拉。

---

## 相关链接

- F大打包 action：https://github.com/ophub/flippy-openwrt-actions
- F大内核：https://github.com/ophub/kernel
- 打包实现：https://github.com/unifreq/openwrt_packit

## 致谢

打包脚本与资源来自 **F大（ophub / unifreq）** 的开源项目，本仓库做了本地化封装以便离线使用与自行修改。