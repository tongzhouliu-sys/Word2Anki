# Word2Anki V1.0

一个帮助你将 Word 单词列表自动转换成带 AI 丰富内容和真人英语发音的 Anki 学习卡片的本地极简工具。

---

## 功能特性

- **Word 自动解析**：自动读取 `.docx` 格式文档，正则提取去重英文单词。
- **Claude API 智能释义**：调用 Claude 生成中文释义、英文释义、例句与记忆技巧。
- **Edge TTS 真人发音**：并发调用微软 TTS 生成真人发音音频。
- **AnkiConnect 自动推送**：自动连接 Anki，智能生成 Deck，自动生成精美的卡片模板，并推送卡片。
- **完备的缓存与断点恢复**：
  - AI 生成的 JSON 数据保存在 `cache/` 中，TTS 发音保存在 `media/` 中。
  - 使用 SQLite 记录处理进度，支持随时终止和断点恢复。

---

## 快速开始

### 1. 准备环境

1. 确保安装了 Python 3.10+。
2. 安装依赖：
   ```bash
   pip3 install -r requirements.txt
   ```

### 2. 配置说明

在项目根目录下，准备以下配置文件：

#### `config.yaml`（基础配置）
项目会自动生成此配置，你可以按需修改：
```yaml
deck_name: "Word2Anki"                    # 导入到 Anki 中的牌组名称
claude_model: "claude-3-5-sonnet-20241022" # 使用的 Claude 模型
voice: "en-US-AvaNeural"                  # TTS 发音人
db_path: "word2anki.db"                   # SQLite 数据库路径
batch_size: 15                            # API 批量处理的单词数量
```

#### `.env`（秘钥配置）
在项目根目录创建 `.env` 文件，填入你的 Claude API 密钥：
```env
CLAUDE_API_KEY=your_claude_api_key_here
```

### 3. 打开并配置 Anki

1. 打开 Anki 桌面版。
2. 安装 **AnkiConnect** 插件（插件代码：`2055492159`）。
3. 重启 Anki，确保 Anki 处于打开运行状态。

### 4. 运行导入指令

执行以下指令，指定你的 Word 单词文件（`.docx`）：
```bash
python3 -m app.cli build words.docx
```

项目运行流程：
1. 自动提取文档内的单词，排重并排序。
2. 检索 SQLite 数据库，过滤已经处理完成的单词（进行断点恢复）。
3. 连接 Anki 并检查模板 `Word2Anki_Basic`，如果不存在则自动创建美观舒适的卡片模板（支持自适应暗黑模式）。
4. 分批从 Claude API 获取释义（已在本地缓存的单词将直接读取 `cache/`，不消耗 API Token）。
5. 异步并发调用 TTS 接口生成发音 MP3。
6. 上传 MP3 并将卡片推送至 Anki。
7. 更新 SQLite 数据库状态。

---

## 目录结构

```text
word2anki/
├── app/
│   ├── cli.py          # 唯一入口
│   ├── importer.py     # 解析 Word，提取去重
│   ├── ai.py           # 批量调用 Claude
│   ├── audio.py        # 并发调用 Edge TTS
│   ├── anki.py         # 推送 Anki，自动建模板
│   └── db.py           # SQLite 状态管理
├── cache/              # 存放 AI 返回的 JSON (apple.json)
├── media/              # 存放 TTS 音频 (apple.mp3)
├── logs/               # 存放运行日志与错误日志 (word2anki.log)
├── config.yaml         # 基础配置
└── .env                # 秘钥配置
```
