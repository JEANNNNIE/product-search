#!/usr/bin/env python3
"""
商品搜索与比价工具 (Product Search & Price Comparison Tool)

Usage:
    python main.py "iPhone 15 Pro 256GB"
    python main.py "机械键盘 青轴 87键"
    python main.py                          # interactive mode
"""

import sys
import argparse
import anthropic
from rich.console import Console
from rich.panel import Panel
from datetime import datetime

console = Console()

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个专业的商品搜索与比价助手。你的核心任务：
根据用户描述的商品，在多个主要电商平台搜索，将相同商品在不同平台的信息汇总对比，
输出一份完整的比价报告。

## 搜索策略

使用 web_search 工具，按以下顺序搜索各大平台：
1. 京东 — 搜索格式："京东 [商品名称] 价格"
2. 淘宝/天猫 — 搜索格式："天猫 [商品名称] 价格"
3. 拼多多 — 搜索格式："拼多多 [商品名称] 价格"
4. 苏宁易购 — 搜索格式："苏宁 [商品名称] 价格"
5. 如有必要，还可搜索亚马逊中国或其他平台

每个平台独立搜索至少一次，力争覆盖3个以上平台。

## 每个商品需收集的信息

- 商品名称及规格（品牌、型号、颜色、版本等）
- 当前价格（原价 / 促销价 / 到手价）
- 预计送达时间（次日达 / 2-3天 / 3-5天等）
- 退款退货政策（是否支持7天无理由，运费谁承担）
- 用户评分及评价数量（若可获取）

## 输出格式（严格遵守）

生成一份 Markdown 格式的完整比价报告：

---

# 🛍️ 商品比价报告

**搜索商品：** {query}
**报告时间：** {time}
**已搜索平台：** 京东、淘宝/天猫、拼多多、苏宁易购

---

## 商品对比（按相关度降序排列）

### 1. [最匹配的商品名称]

> [商品一句话简介]

| 平台 | 价格 | 送达时间 | 退款政策 | 评分 |
|:-----|:-----|:---------|:---------|:-----|
| 京东自营 | ¥xxx | 次日达 | 7天无理由退货，运费险 | 4.9⭐(10万+) |
| 天猫官旗 | ¥xxx | 1-2天 | 7天无理由退货 | 4.8⭐(5万+) |
| 拼多多 | ¥xxx | 3-5天 | 7天无理由退货 | 4.6⭐(2万+) |

- 💰 **最低价：** [平台] ¥xxx
- ⚡ **最快送达：** [平台]（次日达）
- 🛡️ **保障最佳：** [平台]（原因）

---

### 2. [第二相关商品名称]

（同样格式）

---

## 📊 综合购买建议

| 推荐场景 | 推荐平台 | 价格 | 理由 |
|:---------|:---------|:-----|:-----|
| 💰 价格最低 | | ¥xxx | |
| ⚡ 送货最快 | | ¥xxx | |
| 🏆 综合最佳 | | ¥xxx | |

**总结：** [2-3句综合建议，包括哪个平台最值得购买及原因]

---

> ⚠️ **免责声明：** 以上价格随时可能变动，建议购买前在各平台确认最新价格。报告仅供参考。

---

## 注意事项
- 如某平台商品页无法访问，注明原因并跳过
- 价格写明是否含运费
- 如有明显价差，分析可能原因（版本不同、是否正品等）
"""


# ---------------------------------------------------------------------------
# Core search logic
# ---------------------------------------------------------------------------

def run_search(query: str) -> str:
    """Call Claude with web_search to find and compare products."""
    client = anthropic.Anthropic()

    messages = [
        {
            "role": "user",
            "content": (
                f"请帮我在多个电商平台搜索以下商品，并生成完整的比价报告：\n\n"
                f"**商品描述：** {query}\n\n"
                f"请依次搜索京东、淘宝/天猫、拼多多，尽量找到相同款式的商品，"
                f"对比价格、送达时间和退款政策，按相关度降序排列，输出 Markdown 格式报告。"
            ),
        }
    ]

    tools = [{"type": "web_search_20260209", "name": "web_search"}]

    full_text = ""
    header_printed = False
    iteration = 0
    max_iterations = 5  # guard against pause_turn loops

    while iteration < max_iterations:
        iteration += 1

        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                if not header_printed:
                    console.print(
                        "\n[bold green]✓ 搜索完成，正在生成比价报告...[/bold green]\n"
                    )
                    header_printed = True
                print(text, end="", flush=True)
                full_text += text

            response = stream.get_final_message()

        if response.stop_reason == "end_turn":
            break
        elif response.stop_reason == "pause_turn":
            # Server-side tool loop hit limit; re-send to continue
            messages.append({"role": "assistant", "content": response.content})
        else:
            break

    return full_text


# ---------------------------------------------------------------------------
# Report saving
# ---------------------------------------------------------------------------

def save_report(query: str, content: str) -> str:
    """Write the comparison report to a timestamped markdown file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"price_report_{timestamp}.md"

    header = (
        f"# 商品比价报告\n\n"
        f"- **搜索内容：** {query}\n"
        f"- **生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"---\n\n"
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(header + content)

    return filename


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="商品搜索与比价工具 — 输入商品描述，自动搜索多平台并生成比价报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "iPhone 15 Pro 256GB 黑色"
  python main.py "机械键盘 青轴 87键 有线"
  python main.py "男士跑鞋 Nike 43码"
  python main.py                          # 交互模式
        """,
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="商品描述（支持宽泛描述如'蓝牙耳机'或详细描述如'索尼WH-1000XM5'）",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不将报告保存到本地文件",
    )
    args = parser.parse_args()

    # ── Get query ──────────────────────────────────────────────────────────
    if args.query:
        query = args.query.strip()
    else:
        console.print(
            Panel(
                "[bold cyan]🛍️  商品搜索与比价工具[/bold cyan]\n\n"
                "[dim]输入商品描述（宽泛或详细均可），工具将自动搜索京东、淘宝/天猫、\n"
                "拼多多等主流电商平台，汇总价格、送达时间、退款政策，生成比价报告。[/dim]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print()
        query = console.input("[bold]> 请输入商品描述：[/bold] ").strip()

        if not query:
            console.print("[red]错误：商品描述不能为空[/red]")
            sys.exit(1)

    # ── Search ────────────────────────────────────────────────────────────
    console.print()
    console.print(
        Panel(
            f"[bold]搜索中：[/bold] {query}\n"
            f"[dim]正在搜索京东、淘宝/天猫、拼多多等平台，请稍候...[/dim]",
            border_style="blue",
            title="[blue]🔍 搜索中[/blue]",
        )
    )

    result = run_search(query)

    # ── Save ──────────────────────────────────────────────────────────────
    if result and not args.no_save:
        filename = save_report(query, result)
        console.print(f"\n\n[dim]📄 报告已保存至：[bold]{filename}[/bold][/dim]")

    console.print()


if __name__ == "__main__":
    main()
