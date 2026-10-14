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

`Package N1 & X96Max+ (with iStore + DDNS-GO)` 会在 rootfs 里注入五项定制，
并把**镜像的根分区从 1280MB 扩到 4096MB**，**刷完即用，不需要任何手工操作**
（完整说明见下文 [「定制版注入了什么」](#定制版注入了什么n1-x96maxplus-istore)）：

| # | 定制项 | 做法 | 相关文件 |
|---|---|---|---|
| ① | **iStore 应用商店** | 加源 + 把 6 个官方 ipk 预置到 `/usr/share/istore-bootstrap/`，**首次开机由系统自带 opkg 真正安装** | `05-istore-bootstrap` |
| ② | **iStore 菜单全主题对齐** | iStore 是全菜单唯一"没有子菜单的顶层项"，LuCI 对它输出裸 `<li><a data-title=...>`，拿不到 `.nav > .slide > a` 的样式 → 改 `header.htm` 让它与普通顶层项同构（`li.slide > a.menu.exit`），再补点击兜底与按主题族的图标 | `96-istore-theme-align` |
| ③ | **DDNS-GO 的 LuCI 菜单** | rootfs 里 `ddns-go` + `luci-app-ddns-go` 其实都装好了，但官方用 `menu.d/*.json + resources/view/*.js` 新架构，本固件的老式 LuCI 认不了 → 补一个老式 controller + 内嵌 WebUI(:9876) 的 view，并打开 `enabled` | `ddnsgo-luci/` |
| ★ | **根分区 1280MB → 4096MB** | 改的是**打包参数**（不是 rootfs 内容）：CI 里 clone 上游 `unifreq/openwrt_packit`、把 `ROOTFS_MB` 打补丁成 `4096`、再放进 `/opt` 让它跳过自带的 clone | `.github/workflows/package-istore.yml` |

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
| 打包逻辑（如加机型） | `flippy-vendor/openwrt_flippy.sh` |
| **分区尺寸（根分区 ROOTFS_MB）** | `.github/workflows/package-istore.yml` → 「预置并打补丁的 openwrt_packit」那一步（默认 `ROOTFS_MB=4096`，即 4GB） |
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
| iStore 应用数据 / 下载目录的落点 | **已恢复出厂默认（根分区 p2）**，不再改写。如需像旧版那样统一挪到数据分区，把 `system-fixes/95-shared-datadir` 加回 workflow 的注入列表 |

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
| F | ~~应用数据目录自愈~~ | ~~`/etc/hotplug.d/block/95-shared-datadir`~~ | **已取消注入**，见下 |

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
**`OpenWrt` 开放网络**顶上来 —— 用户看到的现象就是"我的 WiFi 不见了，多了个不认识的网络"。

钩子做**三件**事：

1. 把 `ffeXXXXX.sd/` 批量改成 `ffeXXXXX.mmc/`
2. `radio1` 与 `radio0` 路径相同时删掉 `radio1`
3. **改完必须 reload**（`( sleep 8; /sbin/wifi reload ) &`）

> **第 3 条是必须的，早期版本漏了它**（表现：刷机后第一次开机无线一直是死的）。
> 原因：`netifd` 在 boot 早期就已经读过 `/etc/config/wireless` 并 `wifi up` 过一次 ——
> 那时读到的是**没修的 `.sd` 路径**，所以 `radio0` 认领不到 phy。钩子虽然在 28 秒后
> （phy 出现时）把文件改对了，但**只改文件不会让 netifd 重读**，于是本次开机
> `radio0` 会一直停在 `"up": false, "retry_setup_failed": true`，必须主动 reload 一次。
> 延迟 8 秒是为了让 `10-wifi-detect` 先跑完，避免两边同时写配置；
> 全新刷机（路径本来就对）时钩子零动作，不会平白多一次 reload。

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

### ★ 镜像分区扩容：根分区 1280MB → 4096MB

刷完机后 `/`（`ROOTFS`，即 p2）是 **4096MB**。

| 分区 | 卷标 | 旧 | 新 |
|---|---|---|---|
| p1 | `BOOT` | 384MB | 384MB（不变） |
| p2 | **`ROOTFS`** | **1280MB** | **4096MB** |
| p3 | `MMC_ROOTFS2` | 1280MB | 1280MB（不变，A/B 备用槽） |
| p4 | `MMC_SHARED` | 剩余空间 | 剩余空间（16GB 卡上约 9.1GB） |

尺寸全部来自 F大打包脚本 `unifreq/openwrt_packit` 里的三个数
`SKIP_MB=4 / BOOT_MB=384 / ROOTFS_MB=1280`（`mk_s905d_n1.sh`、`mk_s905x3_multi.sh` 各一份）：

```
SIZE = SKIP_MB + BOOT_MB + ROOTFS_MB = 1668MB   → 生成的 .img 总大小
p2   = create_partition 里的 "-1"（占满剩余）    = SIZE − 4 − 384 = 1280MB
/etc/part_size = "SKIP BOOT ROOTFS" 三列          → 写进 rootfs
```

设备**首次开机**时 `/etc/init.d` 里的 `first_run.sh` 读 `/etc/part_size`，再往盘尾补建
p3（尺寸 = 第 3 列）与 p4（占满剩余）。所以只要把 `ROOTFS_MB` 改成 `4096`：
`.img` 变 4484MB、p2 变 4096MB，首启后 p3/p4 自动跟着调整。

额外一处：`files/first_run.sh` 里 p3 的尺寸原本**等于**根分区大小（p3 是 A/B 备用槽），
根分区涨到 4G 后 p3 会白占 4G，所以把它固定回 `ROOTFS2_MiB=1280`，把空间留给 p4 数据区。

> **怎么改到上游脚本的？** 上游是 CI 里 `git clone` 下来的，本来改不到。但主脚本
> `openwrt_flippy.sh` 的 `init_packit_repo()` 写的是 `cd /opt` 然后
> `[[ -d openwrt_packit ]] || git clone ...` —— **`/opt/openwrt_packit` 只要已存在就完全跳过 clone**。
> 于是 workflow 先拉上游、打好补丁、再放进 `/opt`，就让它用了我们这份。
> 补丁用锚点断言（`assert s.count(...) == 1`）保护；构建末尾还会解压一份产物镜像、
> 直接读它的分区表，p2 扇区数必须等于 `8388608`（= 4096MiB），否则整个 job 直接失败。

### F. 应用数据目录自愈 —— 已取消注入

旧版固件用过 `/etc/hotplug.d/block/95-shared-datadir`，把 iStore 系应用
（aria2 / transmission / qbittorrent / verysync / filebrowser / kodexplorer / vsftpd）
的**下载与数据目录**统一改写到数据分区（`MMC_SHARED`，10~12GB），并把
`/opt/transmission`、`/opt/kodexplorer` 做成指向数据分区的软链。

那是在「根分区只有 1.25GB、镜像自带程序就占掉 ~600MB、出厂只剩几十 MB」时的兜底。
现在根分区已经是 **4GB**，而 iStore 应用的**最初安装默认位置本来就是根分区 p2** ——
所以这一项**不再注入**，应用的数据/下载目录保持出厂默认值：

| 应用 | 出厂默认（现在就是这样） |
|---|---|
| aria2 | `/mnt/sda1/aria2` |
| transmission | `/opt/transmission` |
| baidudrive | 下载路径 `/` |
| filebrowser | `/tmp` |
| kodexplorer | `/opt/kodexplorer` |
| verysync / kai | 空（由程序自行决定） |

脚本本体仍保留在 `system-fixes/95-shared-datadir` 备查（含「为什么必须挂
`hotplug.d/block` 而不能放 `uci-defaults`」以及幂等设计的完整说明）；
要重新启用，把它加回 workflow 的注入列表即可。

---

## 相关链接

- F大打包 action：https://github.com/ophub/flippy-openwrt-actions
- F大内核：https://github.com/ophub/kernel
- 打包实现：https://github.com/unifreq/openwrt_packit

## 致谢

打包脚本与资源来自 **F大（ophub / unifreq）** 的开源项目，本仓库做了本地化封装以便离线使用与自行修改。