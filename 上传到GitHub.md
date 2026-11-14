# 上传到 GitHub 并给朋友权限

> **当前状态：本地仓库已经建好了**（分支 `main`，44 个文件已提交）。
> 你**不需要安装 Git**——我在项目里放了一份便携版（`.gittools\mingit`）。
> 你只需要：① 在 GitHub 上建仓库 ② 跑一次 `推送到GitHub.bat` ③ 邀请朋友。

---

## 第 1 步：在 GitHub 上建仓库（1 分钟）

1. 打开 https://github.com/new
2. **Repository name**：`skill-axis-endfield`（名字随意）
3. **Description**：`明日方舟：终末地 技能轴悬浮提示工具`
4. **可见性选 Private**（推荐：朋友够用，也避免素材版权争议）
5. **三个勾都不要打**（Add README / .gitignore / license）——本地已经有了，勾了会冲突
6. 点 **Create repository**

建好后页面会显示仓库地址，形如：

```
https://github.com/你的用户名/skill-axis-endfield.git
```

---

## 第 2 步：推送（双击一个 bat）

双击项目根目录的 **`推送到GitHub.bat`**。

- 第一次运行它会问你 **Repo URL**：把上面那个地址粘进去，回车
- 然后它会执行 `git push`

**会弹浏览器让你登录 GitHub**，授权即可。

> 如果提示输入密码：GitHub 现在不收密码，要用 **Personal Access Token**。
> 生成：GitHub → 头像 → Settings → Developer settings →
> Personal access tokens → Tokens (classic) → Generate new token
> → 勾 `repo` → 生成后复制那串字符，粘贴当密码。

推送成功的标志：最后显示 `main -> main` 且没有 `! [rejected]`。

---

## 第 3 步：给朋友权限

1. 打开你的仓库页面
2. 点顶部 **Settings**
3. 左侧 **Collaborators**（在 "Access" 分组下）
4. 点绿色 **Add people**
5. 输入朋友的 **GitHub 用户名** 或绑定邮箱，选中 → **Add ... to this repository**
6. **朋友必须点邮件里的接受邀请**，否则没有权限

---

## 朋友那边怎么开始

```bash
git clone https://github.com/你的用户名/skill-axis-endfield.git
cd skill-axis-endfield
pip install -r requirements.txt

python tools\fetch_icons.py       # 下载技能图标（必须，否则图标库是空的）
python tools\fetch_portraits.py   # 下载干员立绘

python main.py
```

---

## 仓库里放了什么（重要）

**已包含**（44 个文件，约 550 KB）：

```
main.py  requirements.txt  .gitignore  README.md
使用说明.md  启动说明.txt  上传到GitHub.md  推送到GitHub.bat
app/      23 个模块
tools/    抓素材 / 打包 / 设计稿渲染脚本
启动.bat  调试启动.bat  更新图标库.bat
```

**刻意排除**：

| 排除项 | 原因 |
|---|---|
| `data/icons/`、`data/portraits/` | **游戏素材版权归鹰角**，公开仓库放这些有侵权风险；用 `tools/fetch_*.py` 各自本地下载 |
| `data/*.json` | 你的编队和设置是个人配置 |
| `dist/` | 打包产物 66 MB，二进制不进仓库 |
| `_buildtmp/`、`.gittools/` | PyInstaller 依赖、便携 git，都是工具链 |
| `preview/`、`shots/` | 截图含游戏素材且体积大 |
| `交接摘要.md` | 内部开发笔记，含本机路径 |

> 注意：README 里引用了 `preview/overlay.png` 当展示图，但 preview 被排除了，**图片会 404**。
> 想让它显示：把图片上传到某个 GitHub Issue 里复制链接，或临时把 `preview/overlay.png` 加进仓库（自行权衡版权）。

---

## 以后怎么协作

朋友改了代码：

```bash
git add .
git commit -m "改了什么"
git push
```

你这边拉下来：

```bash
git pull
```

**注意**：`data/` 不共享，所以他的编队和你的不一样——这是设计如此，避免互相覆盖配置。

**冲突了怎么办**：同一文件两人都改过会冲突。简单办法是各改各的模块（`app/` 下按文件分工），冲突概率很低。

---

## 常用 git 命令（用便携版）

便携 git 不在 PATH 里，直接在项目目录开 PowerShell 用全路径：

```powershell
$git = ".\.gittools\mingit\cmd\git.exe"

& $git status
& $git log --oneline
& $git add .
& $git commit -m "说明"
& $git push
& $git pull
```

或者双击 `推送到GitHub.bat`（只做 push）。

---

## 常见问题

**push 报 `Permission denied`**
→ 登录的是别的账号，或仓库不是你的。检查 `git remote -v`。

**push 报 `Updates were rejected`**
→ 远程有你本地没有的提交。先 `git pull --rebase` 再 push。

**朋友 clone 后图标是空的**
→ 没跑 `tools\fetch_icons.py`。程序能开但图标库列表为空就是这个原因。

**想换成自己装的 Git**
→ 装好后直接用 `git` 命令即可，`.gittools` 可以删掉（已在 .gitignore 里）。
