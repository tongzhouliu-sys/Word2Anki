# 🚀 Word2Anki V1.0 极简开发指令 (For AI Coder)

## 〇、 核心原则
1. **一天写完**：只实现核心链路，禁止任何扩展性设计。
2. **Anki 是唯一真相**：SQLite 只记状态，不存业务数据，避免双写同步问题。
3. **文件优于数据库**：缓存和日志直接用文件系统，不占 SQLite 空间。
4. **无 IPA**：V1 放弃音标，专注释义、例句、记忆和发音。

---

## 一、 极简技术栈
仅允许使用以下依赖（写入 `requirements.txt`）：
```text
python-docx
anthropic
edge-tts
requests
```
*(内置使用 `sqlite3`, `json`, `asyncio`, `re`, `pathlib`, `logging`)*

---

## 二、 目录与存储结构
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
├── logs/               # 存放运行日志与错误日志
├── config.yaml         # 基础配置 (deck name, model, voice)
└── .env                # CLAUDE_API_KEY
```

---

## 三、 数据库设计 (SQLite)
**只有一个表 `jobs`，只负责记录任务状态，用于断点恢复。**

```sql
CREATE TABLE IF NOT EXISTS jobs (
    word TEXT PRIMARY KEY,
    status TEXT DEFAULT 'NEW',  -- NEW, DONE, FAILED
    error TEXT                  -- 失败原因
);
```
*注：启动时执行 `PRAGMA journal_mode=WAL;`。*

---

## 四、 卡片结构设计
**放弃 IPA，回归学习本质。**

### 正面 (Front)
```text
{{Word}}
```

### 背面 (Back)
```text
🇨🇳 {{Meaning_CN}}

🇬🇧 {{Meaning_EN}}

📝 {{Example}}

💡 {{Memory_Tip}}

🔊 {{Sound}}
```

---

## 五、 核心模块开发规范

### 1. `importer.py`
- 读取 `.docx`，正则提取纯英文单词 `re.findall(r'\b[a-zA-Z]{2,}\b', text)`。
- 全部转小写 `.lower()`，使用 `set()` 去重。

### 2. `db.py` (状态管理)
- `get_pending_words(all_words)`: 查询 `jobs` 表，过滤掉 `status == 'DONE'` 的词，返回需要处理的列表。
- `mark_done(word)`: 更新状态为 `DONE`。
- `mark_failed(word, error)`: 更新状态为 `FAILED` 并记录 `error`。

### 3. `ai.py` (批量生成与文件缓存)
- **文件缓存**：调用 AI 前，检查 `cache/{word}.json` 是否存在。存在则直接读取，跳过 API。
- **批量请求**：每次取 10-20 个单词发给 Claude。
- **Prompt 约束**：要求返回严格的 JSON 数组：
  ```json
  [{"word": "apple", "meaning_cn": "...", "meaning_en": "...", "example": "...", "memory_tip": "..."}]
  ```
- **降级处理**：如果批量 JSON 解析失败，自动降级为逐个单词请求。
- **保存缓存**：AI 返回成功后，将单个单词的 JSON 写入 `cache/{word}.json`。

### 4. `audio.py` (并发 TTS)
- 检查 `media/{word}.mp3` 是否存在，存在则跳过。
- 使用 `edge-tts`，通过 `asyncio.gather()` 并发处理当前批次的单词。
- 保存到 `media/{word}.mp3`。

### 5. `anki.py` (自动建模板与推送)
- **健康检查**：调用 `invoke('version')` 检查 AnkiConnect。
- **自动建模板**：检查是否存在 `Word2Anki_Basic` 模板。不存在则通过 API 自动创建（包含上述 Front/Back 字段）。
- **推送卡片**：读取 `cache/{word}.json` 和 `media/{word}.mp3`，组装数据推送到指定 Deck。

### 6. `cli.py` (主流程)
- 命令：`word2anki build <file.docx>`
- 流程：
  1. 解析 Word，获取去重后的单词列表。
  2. 查 SQLite，获取 `pending_words`。
  3. 检查 Anki 连接，自动创建模板。
  4. 循环处理 `pending_words`（每批 10-20 个）：
     - 调 AI (带文件缓存) -> 调 TTS (带文件跳过) -> 推 Anki -> 更新 SQLite 状态。
  5. 打印简单的进度条或日志（如 `[120/1830] ✅ apple`）。

---

## 六、 给 AI Coder 的绝对禁令

1. **不要写 Dry Run**，不要写 Stats 统计，不要写复杂的进度条。V1 只需要 `print` 简单的成功/失败日志。
2. **不要维护卡片内容到 SQLite**。SQLite 只有 `jobs` 表。卡片内容全在 `cache/*.json` 和 Anki 里。
3. **不要生成 IPA**。Prompt 里不要提音标，卡片模板里不要有音标字段。
4. **不要使用 ORM**。直接写原生 SQL。
5. **不要做 Provider 抽象**。Claude 就是 Claude，Edge TTS 就是 Edge TTS，直接写死调用。
6. **代码量控制**：整个项目代码量应控制在 500-800 行以内。

---
