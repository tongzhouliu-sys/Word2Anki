# 🚀 Word2Anki V1.0 - 本地个人英语卡片制作工具

一个帮助你将 Word 单词列表自动转换成带 AI 丰富内容和真人英语发音的 Anki 学习卡片的本地极简工具。

---

## 📖 项目说明

Word2Anki 是一个**本地个人化的高效英语词汇背诵卡片制作工具**。它的核心目标是将普通的 Word 单词文档（`.docx`）快速转换为带有 Claude AI 生成的高级丰富释义、例句、记忆法以及 Edge TTS 真人纯正发音的 Anki 卡片。

### 🛠️ 核心架构与设计原则

- **Less is More**：项目采用极简的设计思想，放弃 ORM、FastAPI、Docker 等繁琐抽象，完全面向本地命令行，轻量稳定。
- **Anki 唯一真相**：SQLite 数据库仅记录任务执行状态（`NEW`、`DONE`、`FAILED`）以支撑断点恢复，业务数据均只存放在文件缓存和 Anki 内部。
- **文件级缓存**：
  - AI 生成的 JSON 数据持久化于 `cache/` 中。
  - TTS 发音 MP3 文件缓存于 `media/` 中。
  - 支持随时中断和热启动，已成功的单词绝不重复调用 API，极大地节省 Token 资费。
- **美观大方的卡片设计**：自动在 Anki 中创建并绑定 `Word2Anki_Basic` 模板，内置现代感的无衬线字体，并支持桌面与移动端系统的**自适应暗黑模式**。

---

## 🚀 使用说明与操作指南

### 1. 准备环境

确保您的系统安装了 Python 3.10+，然后在项目根目录下执行以下命令以安装依赖：
```bash
pip3 install -r requirements.txt
```

### 2. 配置文件

在项目根目录下，准备以下配置文件：

#### A. `.env`（秘钥配置）
在根目录下新建 `.env` 文件，填入您的 Claude API 密钥：
```env
CLAUDE_API_KEY=你的Claude_API密钥_在这里
```

#### B. `config.yaml`（基础配置，自动生成）
项目运行时会自动生成该文件，您可以根据需要修改：
```yaml
deck_name: "Word2Anki"                    # 导入到 Anki 中的牌组名称
claude_model: "claude-3-5-sonnet-20241022" # 调用的 Claude 模型
voice: "en-US-AvaNeural"                  # TTS 发音人 (例如: en-US-AvaNeural, en-GB-SoniaNeural)
db_path: "word2anki.db"                   # 状态追踪数据库路径
batch_size: 15                            # Claude 批量请求大小 (推荐 10-20)
```

### 3. 打开并配置 Anki

1. 打开桌面端 **Anki 客户端**。
2. 依次点击菜单：`工具` -> `添加附件` -> `获取插件`。
3. 输入 **AnkiConnect** 的插件代码：`2055492159`。
4. 安装完成后，**重启 Anki** 并保持其处于开启运行状态。

### 4. 运行导入指令

将包含待背单词的 Word 文档（例如 `words.docx`）放置于本地，执行以下指令：
```bash
python3 -m app.cli build words.docx
```

---

## 📁 目录结构

```text
word2anki/
├── app/
│   ├── cli.py          # 唯一入口 (处理终端交互、双日志记录、流水线调度)
│   ├── importer.py     # 解析 Word，正则提取排重单词
│   ├── ai.py           # 批量调用 Claude API 翻译解释
│   ├── audio.py        # 并发调用 Edge TTS 语音生成
│   ├── anki.py         # 自动创建 Deck/Model 模板，推送卡片及媒体
│   └── db.py           # SQLite 状态管理 (断点续传)
├── cache/              # 存放 AI 返回的 JSON (例如: apple.json)
├── media/              # 存放 TTS 音频 (例如: apple.mp3)
├── logs/               # 存放运行日志与错误日志 (word2anki.log)
├── config.yaml         # 基础参数配置
└── .env                # Claude 密钥配置
```

---

## 🎨 卡片效果预览

自动创建的卡片排版如下：

### **正面 (Front)**
- 居中显示超大加粗的英文单词：`{{Word}}`。

### **背面 (Back)**
- **🇨🇳 中文释义**：带有词性标注。
  - 示例：`苹果 (名词)`
- **🇬🇧 英文释义**：纯正简练的英英解释。
- **📝 真实例句**：包含该词的示范句子。
- **💡 记忆技巧**：助记词或词根词缀联想，辅助记忆。
- **🔊 语音发音**：自动在底部加载并播放本地真人发音音频。
