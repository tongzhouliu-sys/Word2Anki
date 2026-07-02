#!/usr/bin/env python3
import sys
import logging
import argparse
from app.anki import check_anki_connection, get_deck_notes, group_existing_notes

def main():
    # Configure logging
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)

    logger = logging.getLogger("group_deck")
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # Align word2anki logger to display logs from app.anki
    anki_logger = logging.getLogger("word2anki")
    anki_logger.setLevel(logging.INFO)
    if not any(isinstance(h, logging.StreamHandler) for h in anki_logger.handlers):
        anki_logger.addHandler(console_handler)

    parser = argparse.ArgumentParser(
        description="Word2Anki Deck Grouping Tool - Split any existing Anki deck into sub-decks in original sequence"
    )
    parser.add_argument("--deck", help="Name of the Anki deck to group")
    parser.add_argument("--size", type=int, help="Number of cards per group")
    args = parser.parse_args()

    print("=" * 60)
    print("🔮 Word2Anki Standalone Deck Grouping Tool")
    print("=" * 60)

    # Check connection to Anki
    if not check_anki_connection():
        print("\n❌ Error: Anki is not running. Please make sure Anki is open and AnkiConnect is active.")
        sys.exit(1)

    deck_name = args.deck
    if not deck_name:
        try:
            deck_name = input("请输入需要分组的 Anki 单词本名称 (例如 Word2Anki): ").strip()
            if not deck_name:
                print("❌ Error: 单词本名称不能为空。")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 任务被用户取消。")
            sys.exit(0)

    # Verify if deck exists and has notes
    existing_notes = get_deck_notes(deck_name)
    if not existing_notes:
        print(f"\n❌ Error: 单词本 '{deck_name}' 不存在或其中没有单词卡片。")
        sys.exit(1)

    print(f"ℹ️  单词本 '{deck_name}' 目前包含 {len(existing_notes)} 张卡片。")

    group_size = args.size
    if not group_size:
        try:
            size_input = input("请输入每组的单词数 [默认: 20]: ").strip()
            if size_input:
                try:
                    group_size = int(size_input)
                    if group_size <= 0:
                        print("⚠️ 无效的分组大小，必须大于 0。将使用默认值 20。")
                        group_size = 20
                except ValueError:
                    print("⚠️ 无效的输入，将使用默认值 20。")
                    group_size = 20
            else:
                group_size = 20
        except KeyboardInterrupt:
            print("\n👋 任务被用户取消。")
            sys.exit(0)

    try:
        confirm = input(f"确认将单词本 '{deck_name}' 按现有顺序分成每组 {group_size} 个吗？(y/n) [y]: ").strip().lower()
        if confirm not in ["", "y", "yes"]:
            print("👋 任务已取消。")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n👋 任务被用户取消。")
        sys.exit(0)

    print("\n🚀 开始分组...")
    try:
        group_existing_notes(deck_name, group_size)
        print("\n🎉 分组完成！所有卡片已在 Anki 中按顺序移入对应的子牌组。")
    except Exception as e:
        print(f"\n❌ 分组过程中出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
