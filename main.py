#!/usr/bin/env python3
"""
商品搜索与比价工具 (Product Search & Price Comparison Tool)

Searches brand official sites, category-specific retailers, and major
e-commerce platforms across China and/or the US market.

Usage:
    python main.py "iPhone 16 Pro 256GB"
    python main.py "Sony WH-1000XM5" --market us
    python main.py "机械键盘 青轴" --market cn
    python main.py "Nike Air Max 270" --market all
    python main.py                             # interactive mode
"""

import sys
import argparse
import anthropic
from rich.console import Console
from rich.panel import Panel
from datetime import datetime

console = Console()

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个专业的全球商品搜索与比价助手，覆盖中国和美国市场。

## 第一步：分析商品类别

拿到用户的商品描述后，先判断：
1. **商品类别**（手机、电脑配件、耳机、服装、运动鞋、图书、家电、美妆、玩具、家具……）
2. **相关品牌/制造商**（如能识别出品牌，优先搜索其官网）
3. **适用市场**（中国、美国、或两者）

## 第二步：按类别制定搜索计划

根据商品类别，制定针对性的搜索来源组合：

### 中国市场（CN）搜索来源

**通用电商（必搜）：**
- 京东自营 — "京东 [商品] 价格 官方"
- 天猫/淘宝 — "天猫 [商品] 旗舰店 价格"
- 拼多多 — "拼多多 [商品] 价格"

**品牌官网（有品牌时必搜）：**
- 直接搜索 "[品牌] 官网 [商品] 价格 中国" 或访问已知官网
- 例：mi.com（小米）、vmall.com（华为）、apple.com/cn（苹果）、
  nike.com.cn（耐克）、adidas.com.cn（阿迪达斯）

**类别专属渠道：**
- 数码/电子：苏宁易购、中关村在线报价
- 图书：当当网、京东图书、豆瓣读书（查口碑）
- 家电：苏宁易购、国美
- 运动鞋/服装：得物（鉴真正品）、识货（折扣信息）
- 美妆：丝芙兰中国、屈臣氏
- 奢侈品/潮牌：官方微信小程序或天猫旗舰店

### 美国市场（US）搜索来源

**通用电商（必搜）：**
- Amazon.com — "site:amazon.com [product] price"
- Walmart.com — "walmart [product] price"
- Target.com — "target [product] price"

**品牌官网（有品牌时必搜）：**
- 直接搜索 "[Brand] official site [product] price" 或已知官网
- 例：apple.com、samsung.com、sony.com、nike.com、adidas.com

**类别专属渠道：**
- 消费电子：Best Buy、Newegg（PC配件）、B&H Photo（相机/摄影）、Adorama
- 运动鞋/服装：Nike.com、Adidas.com、Foot Locker、Dick's Sporting Goods
- 图书：Amazon.com、Barnes & Noble（barnesandnoble.com）
- 家电：Home Depot、Lowe's（工具/建材）、Costco
- 美妆：Sephora.com、Ulta.com
- 游戏：GameStop、Steam（数字游戏）
- 奢侈品：品牌官网 + Nordstrom

## 第三步：执行搜索

- 每个来源单独调用 web_search 一次
- 优先搜索品牌官网和类别专属渠道，再搜大型电商平台
- 力争覆盖 **5 个以上**不同来源
- 对同一商品的不同来源结果进行合并

## 第四步：收集每个来源的信息

| 字段 | 说明 |
|------|------|
| 商品名称及规格 | 品牌、型号、颜色、容量、版本 |
| 价格 | 标价 / 促销价 / 会员价 / 到手价（注明货币） |
| 送达时间 | 次日达 / 2天Prime / 3-5天 / 预计日期 |
| 退款政策 | 天数、是否免运费退货、例外条款 |
| 评分 | 星级 + 评价数量 |
| 是否正品/官方 | 官旗/自营/第三方卖家 |

## 第五步：输出报告格式

生成完整 Markdown 比价报告，结构如下：

---

# 🛍️ 商品比价报告

**搜索商品：** {用户输入}
**报告时间：** {当前时间}
**市场范围：** {中国 / 美国 / 中美两地}
**搜索来源：** {实际搜索过的平台列表}

---

## 商品对比（按相关度降序排列）

### 1. {最匹配商品的完整名称 + 规格}

> {一句话商品简介}

#### 🇨🇳 中国市场

| 渠道 | 价格 | 送达时间 | 退款政策 | 评分 | 备注 |
|:-----|:-----|:---------|:---------|:-----|:-----|
| 京东自营 | ¥xxx | 次日达 | 7天无理由，运费险 | 4.9⭐(10万+) | 官方正品 |
| 苹果官网 | ¥xxx | 1-3个工作日 | 14天无理由 | — | 官方直销 |
| 天猫旗舰店 | ¥xxx | 1-2天 | 7天无理由 | 4.8⭐ | 授权经销 |
| 拼多多 | ¥xxx | 3-5天 | 7天无理由 | 4.5⭐ | 第三方卖家 |

💰 **CN最低价：** [渠道] ¥xxx &nbsp;&nbsp; ⚡ **最快送达：** [渠道]（次日达）

#### 🇺🇸 美国市场

| Retailer | Price | Delivery | Return Policy | Rating | Notes |
|:---------|:------|:---------|:--------------|:-------|:------|
| Apple.com | $xxx | Free 2-day | 14-day free returns | — | Official |
| Amazon | $xxx | 1-2 day Prime | 30-day returns | 4.7⭐(50K+) | Fulfilled by Amazon |
| Best Buy | $xxx | Same-day available | 15-day returns | 4.6⭐ | In-store pickup |
| Walmart | $xxx | 2-day free | 90-day returns | 4.5⭐ | |

💰 **US Best Price：** [Retailer] $xxx &nbsp;&nbsp; ⚡ **Fastest：** [Retailer]

---

### 2. {第二相关商品}

（同样格式，若无美国市场数据则省略对应区块）

---

## 📊 综合购买建议

### 中国市场推荐

| 场景 | 推荐渠道 | 价格 | 理由 |
|:-----|:---------|:-----|:-----|
| 💰 价格最低 | | ¥xxx | |
| ⚡ 最快送达 | | ¥xxx | |
| 🛡️ 保障最佳 | | ¥xxx | 官方售后 |
| 🏆 综合最优 | | ¥xxx | |

### 美国市场推荐（如适用）

| Scenario | Retailer | Price | Reason |
|:---------|:---------|:------|:-------|
| 💰 Best Price | | $xxx | |
| ⚡ Fastest | | $xxx | |
| 🏆 Best Overall | | $xxx | |

### 跨市场对比（如两个市场均有数据）

> 分析中美价差、是否值得海淘/代购、关税和运费估算

---

**总结建议：** {3-5句话的综合购买建议}

---

> ⚠️ 价格随时变动，建议购买前在各渠道确认最新价格。汇率以报告生成时为准。

---

## 重要原则

- 信息无法获取时，注明"暂无数据"而非猜测
- 明确标注价格是否含税、含运费
- 如有明显价差，分析原因（版本差异、正品/仿品风险、关税等）
- 品牌官网价格单独列出，不与第三方混淆
"""


# ---------------------------------------------------------------------------
# Core search logic
# ---------------------------------------------------------------------------

MARKET_LABELS = {
    "cn":  "中国市场",
    "us":  "美国市场",
    "all": "中美两地市场",
}


def build_user_message(query: str, market: str) -> str:
    market_instruction = {
        "cn": (
            "请只搜索**中国市场**的渠道：包括京东、天猫/淘宝、拼多多、苏宁易购，"
            "以及品牌在中国的官网和类别相关的国内专业平台。"
        ),
        "us": (
            "Please search **US market** channels only: including Amazon.com, "
            "Walmart, Target, Best Buy, and the brand's official US website, "
            "plus any category-specific US retailers."
        ),
        "all": (
            "请同时搜索**中国市场**和**美国市场**：\n"
            "- 中国：京东、天猫/淘宝、拼多多、品牌中国官网及类别专属平台\n"
            "- 美国：Amazon.com、Walmart、Best Buy、品牌美国官网及类别专属平台\n"
            "并在报告中进行跨市场价格对比。"
        ),
    }[market]

    return (
        f"请帮我搜索以下商品并生成完整的比价报告：\n\n"
        f"**商品描述：** {query}\n\n"
        f"**市场范围：** {market_instruction}\n\n"
        f"请先判断商品类别和相关品牌，优先搜索品牌官网和类别专属渠道，"
        f"再搜索大型电商平台，力争覆盖5个以上不同来源，"
        f"按相关度降序排列，输出完整 Markdown 比价报告。"
    )


def run_search(query: str, market: str) -> str:
    """Call Claude with web_search to find and compare products."""
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": build_user_message(query, market)}]
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

def save_report(query: str, market: str, content: str) -> str:
    """Write the comparison report to a timestamped markdown file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"price_report_{timestamp}.md"

    header = (
        f"# 商品比价报告\n\n"
        f"- **搜索内容：** {query}\n"
        f"- **市场范围：** {MARKET_LABELS[market]}\n"
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
        description="商品搜索与比价工具 — 搜索品牌官网、专业零售商及主流电商，生成中美两地比价报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "iPhone 16 Pro 256GB"
  python main.py "Sony WH-1000XM5" --market us
  python main.py "机械键盘 青轴 87键" --market cn
  python main.py "Nike Air Max 270 男款 43码" --market all
  python main.py                                     # 交互模式
        """,
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="商品描述（支持宽泛描述如'蓝牙耳机'或详细描述如'Sony WH-1000XM5'）",
    )
    parser.add_argument(
        "--market",
        choices=["cn", "us", "all"],
        default="all",
        help="搜索市场：cn=中国，us=美国，all=两地（默认：all）",
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
        market = args.market
    else:
        console.print(
            Panel(
                "[bold cyan]🛍️  商品搜索与比价工具[/bold cyan]\n\n"
                "[dim]输入商品描述（宽泛或详细均可），工具将自动识别商品类别，\n"
                "搜索品牌官网、类别专属零售商及主流电商平台，\n"
                "生成包含价格、送达时间、退款政策的完整比价报告。[/dim]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print()
        query = console.input("[bold]> 请输入商品描述：[/bold] ").strip()

        if not query:
            console.print("[red]错误：商品描述不能为空[/red]")
            sys.exit(1)

        market_input = console.input(
            "[bold]> 搜索市场 [cn=中国 / us=美国 / all=两地，默认 all]：[/bold] "
        ).strip().lower()
        market = market_input if market_input in ("cn", "us", "all") else "all"

    # ── Search ────────────────────────────────────────────────────────────
    market_label = MARKET_LABELS[market]
    console.print()
    console.print(
        Panel(
            f"[bold]搜索：[/bold] {query}\n"
            f"[bold]市场：[/bold] {market_label}\n"
            f"[dim]正在识别商品类别，搜索品牌官网、专业零售商及电商平台...[/dim]",
            border_style="blue",
            title="[blue]🔍 搜索中[/blue]",
        )
    )

    result = run_search(query, market)

    # ── Save ──────────────────────────────────────────────────────────────
    if result and not args.no_save:
        filename = save_report(query, market, result)
        console.print(f"\n\n[dim]📄 报告已保存至：[bold]{filename}[/bold][/dim]")

    console.print()


if __name__ == "__main__":
    main()
