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

### 方式一：在线打包（默认）

1. 打开仓库的 **Actions** → `Package N1 & X96Max+ (self-contained)`
2. 点 **Run workflow**，参数保持默认即可
3. 等待约 5~10 分钟
4. 到 **Releases** → tag `N1-X96MaxPlus` 下载固件

### 方式二：完全离线打包（长期可用）

先把你自己的 rootfs 上传到本仓库的 Releases，tag 设为 `ROOTFS`，然后：

1. 触发 workflow，在 `rootfs_file` 填那个资产文件名（如 `openwrt-armsr-armv8-generic-rootfs.tar.gz`）
2. 此时**不再访问 ophub**，只依赖你上传的 rootfs + 自己的脚本

> 这样即使 F大（ophub/unifreq）全部下架，本仓库仍可正常打包。

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

## 相关链接

- F大打包 action：https://github.com/ophub/flippy-openwrt-actions
- F大内核：https://github.com/ophub/kernel
- 打包实现：https://github.com/unifreq/openwrt_packit

## 致谢

打包脚本与资源来自 **F大（ophub / unifreq）** 的开源项目，本仓库做了本地化封装以便离线使用与自行修改。