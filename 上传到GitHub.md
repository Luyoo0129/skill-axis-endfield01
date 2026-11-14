# 上传到 GitHub 并给朋友权限

> 说明：这台机器上**没有安装 Git**，所以下面的命令需要你在装好 Git 后自己执行（或者让我代跑，但推送那一步要你登录）。

---

## 第 1 步：安装 Git（三选一）

**方式 A：winget（最快）**

在 PowerShell 里执行：

```powershell
winget install --id Git.Git -e --source winget
```

装完**关掉再重开** PowerShell（让 PATH 生效）。

**方式 B：官网下载**

打开 https://git-scm.com/download/win ，下载 64-bit 安装包，一路默认下一步。

**方式 C：GitHub Desktop**

https://desktop.github.com/ ，图形界面，适合不想敲命令的人。

验证是否装好：

```powershell
git --version
```

---

## 第 2 步：告诉 Git 你是谁

只需要设置一次：

```powershell
git config --global user.name "你的名字"
git config --global user.email "你的GitHub邮箱"
```

---

## 第 3 步：在 GitHub 上建仓库

1. 打开 https://github.com/new
2. **Repository name** 填：`skill-axis-endfield`（或你喜欢的名字）
3. **Description** 可填：`明日方舟：终末地 技能轴悬浮提示工具`
4. **权限一定要选 Public 或 Private**：
   - 选 **Private**（推荐，朋友够用，也不公开素材问题）
5. **不要**勾选 "Add a README file"、"Add .gitignore"、"Choose a license"
   （本地已经准备好了，勾了会冲突）
6. 点 **Create repository**

创建后页面会给你一个地址，形如：

```
https://github.com/你的用户名/skill-axis-endfield.git
```

---

## 第 4 步：把本地项目传上去

在项目目录里执行（把地址换成你自己的）：

```powershell
cd "F:\dsh work\skill-axis"

git init
git add .
git commit -m "初始提交：技能轴提示器"

git branch -M main
git remote add origin https://github.com/你的用户名/skill-axis-endfield.git
git push -u origin main
```

第一次 `git push` 会弹窗让你登录 GitHub（浏览器授权），按提示走完即可。

> 如果弹窗没出现、一直提示输入密码：GitHub 现在不接受密码，要用 **Personal Access Token**。
> 生成方式：GitHub → 右上头像 → Settings → Developer settings →
> Personal access tokens → Tokens (classic) → Generate new token → 勾选 `repo` → 复制生成的串当密码粘贴。

---

## 第 5 步：给朋友权限

1. 打开你的仓库页面
2. 点 **Settings**（顶部标签栏）
3. 左侧菜单点 **Collaborators**（在 "Access" 分组下）
4. 点绿色按钮 **Add people**
5. 输入朋友的 **GitHub 用户名** 或邮箱，选中后点 **Add ... to this repository**
6. 朋友会收到邮件邀请，**他必须点接受** 才有权限

朋友接受后，他这样拉代码：

```powershell
git clone https://github.com/你的用户名/skill-axis-endfield.git
cd skill-axis-endfield
pip install -r requirements.txt
python tools\fetch_icons.py
python tools\fetch_portraits.py
python main.py
```

---

## 关于仓库里放什么（重要）

`.gitignore` 已经配好，**以下内容不会上传**：

| 排除项 | 原因 |
|---|---|
| `data/icons/`、`data/portraits/` | **游戏素材版权归鹰角**，公开仓库放这些有侵权风险；用 `tools/fetch_*.py` 各自本地下载 |
| `data/*.json` | 你的编队和设置是个人配置，没必要共享 |
| `dist/` | 打包产物 66 MB，二进制不该进仓库 |
| `_buildtmp/` | PyInstaller 依赖 19 MB |
| `preview/`、`shots/` | 截图里含游戏素材，且体积大 |
| `__pycache__/` | 编译缓存 |

**会**上传的：`app/`、`tools/`、`main.py`、`*.bat`、`*.md`、`requirements.txt`、`.gitignore`。
总共约 **300 KB**，很轻。

> README 里引用了 `preview/overlay.png` 做展示图，但 preview 被排除了，图片会 404。
> 如果想让 README 有图：把 `preview/overlay.png` 单独放行，或者上传到 GitHub Issue 里拿图片链接。
> 简单做法：在 `.gitignore` 里删掉 `preview/` 那行，只保留这一张图（仍含游戏图标，自行权衡）。

---

## 以后怎么同步

朋友改了代码 → 他那边：

```powershell
git add .
git commit -m "说明改了什么"
git push
```

你这边拉下来：

```powershell
git pull
```

**注意**：`data/` 不共享，所以他的编队和你的不一样，这是预期行为。

---

## 常见问题

**push 报 `remote: Permission to ... denied`**
→ 那个仓库不是你的，或者登录的是别的账号。检查 `git remote -v` 的地址和用户名。

**push 报 `Updates were rejected`**
→ 远程有你本地没有的提交，先 `git pull --rebase` 再 push。

**朋友 clone 后程序起不来**
→ 十有八九是没跑 `fetch_icons.py` / `fetch_portraits.py`，`data/icons` 是空的。
程序能跑但图标列表为空就是这个原因。
