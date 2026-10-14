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

`Package N1 & X96Max+ (with iStore + DDNS-GO)` 会在 rootfs 里注入六项定制，
**刷完即用，不需要任何手工操作**（完整六项说明见下文
[「定制版注入了什么」](#定制版注入了什么n1-x96maxplus-istore)）：

| # | 定制项 | 做法 | 相关文件 |
|---|---|---|---|
| ① | **iStore 应用商店** | 加源 + 把 6 个官方 ipk 预置到 `/usr/share/istore-bootstrap/`，**首次开机由系统自带 opkg 真正安装** | `05-istore-bootstrap` |
| ② | **iStore 菜单全主题对齐** | iStore 是全菜单唯一"没有子菜单的顶层项"，LuCI 对它输出裸 `<li><a data-title=...>`，拿不到 `.nav > .slide > a` 的样式 → 改 `header.htm` 让它与普通顶层项同构（`li.slide > a.menu.exit`），再补点击兜底与按主题族的图标 | `96-istore-theme-align` |
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
| iStore 侧边栏对齐与图标（全主题） | `istore-bootstrap/96-istore-theme-align`（argon 系 `ssr:\e906`、mcat/atmaterial/tomato `advancedtomato:\e018`、ifit 沿用 `HomeLedeIcomoon:\e903` + `#26C6DA`） |
| DDNS-GO 的菜单入口与页面 | `ddnsgo-luci/rootfs/usr/lib/lua/luci/...` |
| DDNS-GO 的启用钩子 | `ddnsgo-luci/zz-ddnsgo-luci` |
| 应用数据/下载目录的落点（默认数据分区） | `system-fixes/95-shared-datadir` |

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
| B | **iStore 侧边栏对齐与图标（全主题）** | `/etc/uci-defaults/96-istore-theme-align` | 裸顶层项 → 与普通顶层项同构；再补点击兜底 + 按主题族补图标。见下 |
| C | DDNS-GO 的 LuCI 入口 | `ddnsgo-luci/` + `/etc/uci-defaults/zz-ddnsgo-luci` | 官方包用 `menu.d` 新架构，本固件的 `createindex()` 只扫 `controller/*.lua`，菜单天生不出现 |
| D | **无线路径自愈** | `/etc/hotplug.d/ieee80211/05-wifi-path-fix` | 见下 |
| E | **样式表版本后缀（全主题）** | `/etc/uci-defaults/98-theme-css-cachebust` | 见下 |
| F | **应用数据目录自愈** | `/etc/hotplug.d/block/95-shared-datadir` | 见下 |

### B. iStore 侧边栏对齐（全主题）

LuCI 的 `render_topmenu()` 对**没有子菜单的顶层项**输出的是裸 `<li>`：

```html
<li><a data-title="iStore" href="/cgi-bin/luci/admin/store">iStore</a></li>
```

而所有主题的侧边栏样式（`padding-left` 缩进、盒模型、hover、图标字体的 `font-family`）
统统挂在 `.main > .main-left > .nav > .slide > a(.menu)` 上。
整个 admin 菜单里**只有 iStore 是这种裸项**（Logout / Reboot 也是裸项，但主题作者
逐个 `data-title` 手工补过 CSS，唯独漏了 iStore），所以它文字贴最左边、而且没有图标。
旧版固件只给 ifit 追加过一段 iStore 专用 CSS —— 于是表现为「**只有 ifit 能对齐，其它主题全歪**」。

修复分四步，**全部与具体主题无关**：

| 步骤 | 做法 |
|---|---|
| ① 结构 | 改 `header.htm` 的渲染层：`<li><a data-title=...>` → `<li class="slide"><a class="menu exit" data-title=...>`，与普通顶层项同构 → 缩进 / 盒模型 / hover / 图标字体全部自动继承 |
| ② 行为 | 各主题对 `.slide > .menu` 的 `click` 一律 `return false`（手风琴），叶子项没有子菜单可展开 → 在**捕获阶段**抢先放行、直接跳转。用 `.exit` 作标记，因为 design 主题本身就有 `if(!menu.hasClass("exit"))` |
| ③ tomato 特例 | `tomato/js/script.js` 里有 `$( ".slide > a" ).removeAttr("href")`，会把叶子项的 `href` 一并删掉 → 排除 `.exit` |
| ④ 图标 | 结构改好后 iStore 已继承主题图标字体的 `font-family`，只差一个字形码：argon 系取 `ssr` 的 `\e906`(dashboard 宫格)，mcat / atmaterial / tomato 取 `advancedtomato` 的 `\e018`(加号)；`material` 侧边栏本来就没有任何图标、`design` 自带 `.menu2`、`rosy` 把叶子项移出 `.nav` → 这三者保持原样；ifit 沿用旧版的青色图标（`HomeLedeIcomoon` 的 `\e903` + `#26C6DA`），缩进改为跟随主题 |

> 效果不是"把所有主题强行统一成一个缩进值"，而是"**每个主题内部自洽**"：
> 各主题继承到的缩进并不相同（argon 40px、argon_dark 56px、ifit 35px、material 16px、
> design 50px…），但都与同主题其它项**一致**——这正是用户要的"对齐"。
> 另外 `bootstrap` / `bootstrap_mod` 是宽屏水平菜单，iStore 的位置本来就正确。

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

### E. 样式表版本后缀（全主题）

uhttpd 只发 `ETag` / `Last-Modified`，**不发 `Cache-Control` / `Expires`**。按 RFC 7234 §4.2.2，
浏览器会对这类响应做"启发式缓存"，有效期约 `(缓存时刻 − Last-Modified) × 10%`。
老 `style.css` 的 `Last-Modified` 是出厂日期，缓存一次能"新鲜"几十天，**期间根本不回服务器验证** ——
于是补丁明明生效了，用户看到的还是旧界面。

钩子给**所有被打过补丁的主题**的 `header.htm` 里的 `<link ... .css>` 加上
`?v=<该主题 style.css 的 mtime>`，URL 一变浏览器必然重拉。本来就用动态版本号的主题
（argon_dark 系的 `?v=<%=math.random(1,100000)%>`、design 的 `?v=<%=ver.luciversion%>`）自动跳过。

### F. 应用数据目录自愈（根分区被灌满的坑）

根分区（`ROOTFS`）只有 **1.25GB**，而镜像本身就自带约 **600MB**
（OpenList 136M、dockerd 70M、rclone 68M、containerd 45M、sing-box 42M、gost 35M、
node 33M、verysync 32M、xray 30M…），**出厂就只剩几十 MB 空闲**。
开机后从 iStore 装的应用又动辄 200MB 级（`kai_session` 195MB、`linkease-full` 149MB）。

而 iStore 系应用的**出厂默认目录几乎全是错的**：

| 应用 | 出厂默认 | 问题 |
|---|---|---|
| aria2 | `/mnt/sda1/aria2` | 路径根本不存在 |
| transmission | `/opt/transmission` | 在根分区 |
| baidudrive | 下载路径 `/` | 根分区 |
| filebrowser | `/tmp` | 内存盘 |
| kodexplorer | `/opt/kodexplorer` | 在根分区 |
| verysync / kai | 空 | 落到默认位置 |

`/etc/hotplug.d/block/95-shared-datadir` 在数据分区（`MMC_SHARED`，10~12GB）挂载后，
把这些目录统一指到 `…/downloads/…` 与 `…/data/…`，并把 `/opt/transmission`、
`/opt/kodexplorer` 做成指向数据分区的软链（照抄 flippy 已有的 `/opt/docker` 写法）。

> **为什么是 `hotplug.d` 而不是 `uci-defaults`**：`uci-defaults` 在 `/etc/init.d/boot`
> （START=10）里执行，而挂载数据分区的 `/etc/init.d/fstab` 是 START=11 —— 那时
> 分区还没挂上，`mkdir` 会把目录建到根分区上（随后被挂载遮住，等于白建）。
> `block` 的 add 事件才是"分区已就绪"的时刻，`95-` 又排在原生 `10-mount` 之后。

钩子是**幂等**的：只在当前值为空、或为上面这些已知的错误出厂默认值时才改写，
你在 LuCI 里自己改过的目录一律不动。挂载点按分区标签 `MMC_SHARED` 解析，
换启动介质导致设备名变化也不会失准。

---

## 相关链接

- F大打包 action：https://github.com/ophub/flippy-openwrt-actions
- F大内核：https://github.com/ophub/kernel
- 打包实现：https://github.com/unifreq/openwrt_packit

## 致谢

打包脚本与资源来自 **F大（ophub / unifreq）** 的开源项目，本仓库做了本地化封装以便离线使用与自行修改。