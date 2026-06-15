from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "data/raw/rag_paper_arxiv_2005_11401.pdf": "https://arxiv.org/pdf/2005.11401",
    "data/raw/attention_is_all_you_need_arxiv_1706_03762.pdf": "https://arxiv.org/pdf/1706.03762",
    "data/raw/bert_arxiv_1810_04805.pdf": "https://arxiv.org/pdf/1810.04805",
    "data/raw/gpt3_arxiv_2005_14165.pdf": "https://arxiv.org/pdf/2005.14165",
    "data/raw/alice_project_gutenberg.txt": "https://www.gutenberg.org/cache/epub/11/pg11.txt",
    "data/web/deepseek_api_docs.html": "https://api-docs.deepseek.com/",
    "data/web/wikipedia_artificial_intelligence.html": "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "data/web/wikipedia_go_game.html": "https://en.wikipedia.org/wiki/Go_(game)",
    "data/web/wikipedia_minecraft.html": "https://en.wikipedia.org/wiki/Minecraft",
}


def main() -> None:
    for relative_path, url in SOURCES.items():
        target = ROOT / relative_path
        if target.exists():
            print(f"skip {relative_path}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # 公开网页有些会检查 User-Agent，这里只设置最小请求头。
        request = Request(url, headers={"User-Agent": "personal-knowledge-agent/0.1"})
        with urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
        print(f"downloaded {relative_path}")


if __name__ == "__main__":
    main()
