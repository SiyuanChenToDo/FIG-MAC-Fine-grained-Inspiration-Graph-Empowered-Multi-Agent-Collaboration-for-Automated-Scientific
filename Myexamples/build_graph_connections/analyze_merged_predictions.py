import argparse
import csv
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class NumericSummary:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def add(self, value: float) -> None:
        self.count += 1
        if self.min_value is None or value < self.min_value:
            self.min_value = value
        if self.max_value is None or value > self.max_value:
            self.max_value = value

        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

    def summary(self) -> Dict[str, float]:
        if self.count == 0:
            return {}
        variance = self.m2 / (self.count - 1) if self.count > 1 else 0.0
        return {
            "numeric_count": self.count,
            "min": self.min_value,
            "max": self.max_value,
            "mean": self.mean,
            "stddev": math.sqrt(variance),
        }


@dataclass
class ColumnStats:
    sample_size: int
    preview_width: int = 120
    non_null_count: int = 0
    null_count: int = 0
    samples: List[str] = field(default_factory=list)
    numeric_summary: NumericSummary = field(default_factory=NumericSummary)

    def update(self, value: Optional[str]) -> None:
        if value is None:
            self.null_count += 1
            return
        stripped = value.strip()
        if stripped == "":
            self.null_count += 1
            return

        self.non_null_count += 1
        self._update_samples(stripped)

        numeric_value = try_parse_float(stripped)
        if numeric_value is not None:
            self.numeric_summary.add(numeric_value)

    def _update_samples(self, value: str) -> None:
        if self.sample_size <= 0:
            return
        if len(self.samples) < self.sample_size:
            self.samples.append(value)
            return
        idx = random.randint(0, self.non_null_count - 1)
        if idx < self.sample_size:
            self.samples[idx] = value

    def summary(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "non_null": self.non_null_count,
            "null": self.null_count,
            "sample_values": [truncate_text(val, self.preview_width) for val in self.samples],
        }
        numeric_stats = self.numeric_summary.summary()
        if numeric_stats:
            data.update(numeric_stats)
        return data


def try_parse_float(text: str) -> Optional[float]:
    candidate = text.replace(",", "")
    try:
        value = float(candidate)
    except ValueError:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def truncate_text(text: str, max_length: int = 120) -> str:
    if max_length <= 0:
        return text
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3] + "..."


def truncate_row(row: Dict[str, Optional[str]], max_length: int) -> Dict[str, Optional[str]]:
    return {
        key: truncate_text(value, max_length) if isinstance(value, str) else value
        for key, value in row.items()
    }


def format_float(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.6g}"


def non_negative_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("参数必须是非负整数")
    return value


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对 merged_predictions.csv 进行流式统计分析")
    default_csv = Path(__file__).with_name("corrected_predictions_with_reasoning_20251112_final.csv")
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=default_csv,
        help="目标 CSV 文件路径，默认为脚本同目录下的 corrected_predictions_with_reasoning_20251112_final.csv",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="读取文件时使用的编码，默认 utf-8",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="CSV 分隔符，默认逗号",
    )
    parser.add_argument(
        "--quotechar",
        default='"',
        help="CSV 引号字符，默认双引号",
    )
    parser.add_argument(
        "--sample-values",
        type=non_negative_int,
        default=5,
        dest="sample_values",
        help="每列保存的示例值数量（使用蓄水池采样），默认 5",
    )
    parser.add_argument(
        "--head-rows",
        type=non_negative_int,
        default=5,
        dest="head_rows",
        help="输出前若干行内容预览，默认 5",
    )
    parser.add_argument(
        "--row-sample",
        type=non_negative_int,
        default=0,
        dest="row_sample",
        help="额外使用蓄水池采样输出的随机行数，默认 0",
    )
    parser.add_argument(
        "--max-rows",
        type=non_negative_int,
        default=0,
        dest="max_rows",
        help="最多处理的行数，0 表示处理全部行",
    )
    parser.add_argument(
        "--preview-width",
        type=non_negative_int,
        default=120,
        dest="preview_width",
        help="预览文本的最大字符长度，0 表示不截断，默认 120",
    )
    parser.add_argument(
        "--count-only",
        action="store_true",
        dest="count_only",
        help="仅统计行数和列信息，不执行列统计与示例输出",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        dest="random_seed",
        help="随机数种子，默认 42，保证采样可复现",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        dest="json_output",
        help="如指定，则将统计结果导出为 JSON 文件",
    )
    return parser.parse_args()


def build_column_stats(
    fieldnames: Sequence[str],
    sample_size: int,
    preview_width: int,
) -> Dict[str, ColumnStats]:
    return {
        name: ColumnStats(sample_size=sample_size, preview_width=preview_width)
        for name in fieldnames
    }


def analyze_csv(args: argparse.Namespace) -> Dict[str, Any]:
    csv_path = args.csv_path.resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"未找到文件: {csv_path}")

    random.seed(args.random_seed)

    with csv_path.open("r", encoding=args.encoding, newline="") as f:
        reader = csv.DictReader(
            f,
            delimiter=args.delimiter,
            quotechar=(args.quotechar if args.quotechar else None),
        )
        if reader.fieldnames is None:
            raise ValueError("CSV 文件缺少表头，无法进行统计分析")
        fieldnames = reader.fieldnames
        column_stats = (
            build_column_stats(fieldnames, args.sample_values, args.preview_width)
            if not args.count_only
            else None
        )

        processed_rows = 0
        head_rows: List[Dict[str, Optional[str]]] = []
        row_samples: List[Dict[str, Optional[str]]] = []
        limited_by_max_rows = False

        for row in reader:
            if args.max_rows and processed_rows >= args.max_rows:
                limited_by_max_rows = True
                break

            processed_rows += 1

            if column_stats is not None:
                for name, stats in column_stats.items():
                    stats.update(row.get(name))

            if not args.count_only and args.head_rows and len(head_rows) < args.head_rows:
                head_rows.append(truncate_row(row, args.preview_width))

            if not args.count_only and args.row_sample:
                truncated = truncate_row(row, args.preview_width)
                if len(row_samples) < args.row_sample:
                    row_samples.append(truncated)
                else:
                    idx = random.randint(0, processed_rows - 1)
                    if idx < args.row_sample:
                        row_samples[idx] = truncated

    result: Dict[str, Any] = {
        "file": str(csv_path),
        "encoding": args.encoding,
        "delimiter": args.delimiter,
        "quotechar": args.quotechar,
        "fieldnames": fieldnames,
        "total_columns": len(fieldnames),
        "rows_processed": processed_rows,
        "limited_by_max_rows": limited_by_max_rows,
        "columns": {name: stats.summary() for name, stats in column_stats.items()} if column_stats else {},
        "head_rows": head_rows if not args.count_only else [],
        "count_only": args.count_only,
    }
    if row_samples:
        result["row_samples"] = row_samples
    return result


def save_json(result: Dict[str, Any], json_path: Path) -> None:
    json_path = json_path.expanduser().resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def print_summary(result: Dict[str, Any]) -> None:
    print(f"文件: {result['file']}")
    print(f"编码: {result['encoding']}")
    print(f"分隔符: {result['delimiter']!r}")
    print(f"引号字符: {result['quotechar']!r}")
    print(f"列数量: {result['total_columns']}")
    print(f"已处理行数: {result['rows_processed']}")
    if result["limited_by_max_rows"]:
        print("注意: 由于设置了 --max-rows，仅处理了部分数据。")

    count_only = result.get("count_only", False)

    if count_only:
        print("\n当前处于 count-only 模式，未计算列统计信息与示例内容。")
        return

    print("\n列统计信息:")
    for name, stats in result["columns"].items():
        print(f"- {name}")
        print(f"    非空值数量: {stats.get('non_null', 0)}")
        print(f"    空值数量: {stats.get('null', 0)}")
        numeric_count = stats.get("numeric_count")
        if numeric_count:
            print("    数值统计:")
            print(f"        样本数量: {numeric_count}")
            print(f"        最小值: {format_float(stats.get('min'))}")
            print(f"        最大值: {format_float(stats.get('max'))}")
            print(f"        平均值: {format_float(stats.get('mean'))}")
            print(f"        标准差: {format_float(stats.get('stddev'))}")
        samples = stats.get("sample_values") or []
        if samples:
            print("    示例值:")
            for sample in samples:
                print(f"        - {sample}")

    head_rows = result.get("head_rows") or []
    if head_rows:
        print(f"\n前 {len(head_rows)} 行示例 (截断至预览宽度):")
        print(json.dumps(head_rows, ensure_ascii=False, indent=2))

    row_samples = result.get("row_samples") or []
    if row_samples:
        print(f"\n随机采样的 {len(row_samples)} 行:")
        print(json.dumps(row_samples, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_arguments()
    result = analyze_csv(args)
    if args.json_output:
        save_json(result, args.json_output)
        print(f"\n已将统计结果写入: {args.json_output.resolve()}")
    print_summary(result)


if __name__ == "__main__":
    main()
