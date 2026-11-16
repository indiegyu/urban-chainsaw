# korean-csv-cleaner-lite

**Open and clean Korean CSV exports — offline, zero dependencies, MIT.**

Two jobs eat an afternoon on almost every Korean office data task: **opening the
file you were sent**, and **making it consistent enough to merge, upload or hand
over**. This is the small, readable version of a tool I use for both — standard
library only, so it runs on any machine with Python 3.8+ and nothing installed.

```
$ python -m kcsvlite inspect examples/report_cp949.csv
file      : examples/report_cp949.csv
encoding  : cp949
delimiter : ','
rows      : 10 x 5
header    : row 3 -> 고객명 | 휴대폰_번호 | 가입일 | 누적구매액 | 수신동의
first rows:
  1: 2026년 1월 고객 명세
  2:
  3: 고객명 | 휴대폰_번호 | 가입일 | 누적구매액 | 수신동의

$ python -m kcsvlite clean examples/report_cp949.csv -o clean.csv --dedupe
examples/report_cp949.csv: read 10 rows as cp949
drop_blank_rows: 2 removed
promote_header: used row 3 as header (dropped: 2026년 1월 고객 명세)
clean_text: 2 cells (invisible chars, full-width, spacing)
dedupe: 1 duplicates removed, 6->5 rows
written   : clean.csv  (5 rows x 5 columns, utf-8-sig)
```

No upload, no account, no telemetry — the file never leaves your machine, and
every run prints what it changed.

## The three problems it solves

| What you see | What this does |
|---|---|
| `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc1` | Detects CP949 / EUC-KR / UTF-8 / UTF-8-with-BOM and reads the file |
| A file that opens as `Ã«Â³Â´êÂ³` in another program | Writes the result as UTF-8 **with** the BOM Korean Excel needs |
| A title row (`2026년 1월 고객 명세`), a blank row, *then* the header | Scores the first rows and promotes the real header to the top |
| `02 555 0100` with a non-breaking space, `서연상회` with a soft hyphen inside, `１２３０００` in full-width digits | Normalises the text so lookups and `VLOOKUP` matches actually match |
| The same row exported twice | `--dedupe` drops exact duplicates and says how many |
| A CSV with 30 rows of empty cells at the bottom | Blank rows go, trailing empty columns go, short rows are padded |

## Install

Nothing to install — the package is the two modules in `kcsvlite/`.

```bash
git clone https://github.com/indiegyu/urban-chainsaw.git
cd urban-chainsaw/products/korean-csv-cleaner-lite
python -m kcsvlite inspect examples/report_cp949.csv
python run_demo.py                       # both samples, with change logs
python -m unittest discover -s tests -v  # 54 tests, offline
```

`python -m unittest discover -s tests` prints:

```
Ran 54 tests in 0.009s

OK
```

54 tests, no network, no fixtures to download — the samples in `examples/` are
the fixtures.

## Use it as a library

```python
from kcsvlite import ChangeLog, clean_rows, read_rows, write_rows

rows, encoding, separator = read_rows("report_cp949.csv")   # raw grid, encoding detected
log = ChangeLog()
header, body = clean_rows(rows, dedupe=True, log=log)

write_rows([header] + body, "clean.csv")                    # utf-8-sig by default
print(encoding, separator, len(body))
print(log.summary())
```

One value, one function:

```python
from kcsvlite import clean_text, detect_encoding, detect_header_row, is_blank

detect_encoding(open("legacy.csv", "rb").read())  # 'cp949'
clean_text("02\u00a0555\u00a00100")               # '02 555 0100'
clean_text("１２３")                                # '123'
is_blank("\u00a0")                                # True
```

## Commands

```bash
python -m kcsvlite inspect FILE                       # encoding, delimiter, shape, header row
python -m kcsvlite clean   FILE [-o OUT] [options]    # normalise + write a change log
```

| `clean` option | Meaning |
|---|---|
| `-o, --output PATH` | Output file (default: `FILE_clean.csv`) |
| `--dedupe` | Drop exact duplicate rows after cleaning |
| `--header-row N` | Force the 0-based row that holds the header |
| `--delimiter C` | Force the separator (`;`, `\t`, `\|`) |
| `--no-nfkc` | Keep full-width characters as they are |

## Design rules

- **It never guesses silently.** The encoding is detected from a BOM first, then
  by strict decoding in a fixed order; a byte sequence nothing can read falls
  back to latin-1 and says so, rather than half-decoding into mojibake.
- **No header assumption on read.** The file is read as a raw grid, because the
  title row a Korean export puts above the header is part of the data, and a
  reader that eats row 0 cannot give it back.
- **The order of the steps is the design.** Blank rows go first (so an empty row
  cannot win the header vote), then the header, then the cell text, then
  duplicates — cleaning text before comparing is what makes exact duplicates
  exact.
- **Every step is logged**, with row counts, next to the file it produced.
- **Zero dependencies.** Standard library only: `csv`, `re`, `unicodedata`,
  `argparse`. Nothing to install, nothing to keep updated, nothing that needs a
  network.

## What it will not do

- Read `.xlsx` / `.xlsm` (that needs a library — see the full version below).
- Guess whether `03/04/2024` is March 4th or April 3rd. That is a question for
  the person who made the file.
- Fuzzy-match `(주)대한물산` to `대한물산`, or merge duplicates that differ by a
  character. Exact duplicates only.
- Fix meaning. It fixes form: two different companies with the same name stay
  two rows.

## Full version

This repo is the free, dependency-free core — encoding, header, text, blanks,
duplicates. The full toolkit adds the rest of what a weekly data-cleanup job
needs, in six modules with a CLI and a 40-page guide:

- `.xlsx` / `.xlsm` reading and writing (multi-sheet, `_source_sheet` column)
- **merge** a folder of monthly files in mixed encodings into one table
- **split** a 40,000-row file into upload-sized pieces that keep the header
- phone (`+82 10-1234-5678` → `010-1234-5678`), date (`2024년 1월 5일`,
  `24-1-5`, `20240105`, Excel serial) and amount (`1,200,000원`, `(1,500)` →
  −1500) normalisation
- fuzzy company-name merging with a threshold, and RRN masking (`900101-1******`)
- 64 offline tests and a per-run change report as CSV

**→ [Korean / Global CSV & Excel Cleaner + Batch Processor Toolkit](https://psgfanatic8.gumroad.com/l/korean-csv-excel-cleaner-batch-processor)** ($9, one-time)

If the lite version solves your file, the full one solves the next twenty.

## 한국어 요약

한국 사무실에서 표 하나 정리하려고 반나절 쓰는 일들 — **CP949/EUC-KR 파일이
안 열릴 때**, 엑셀 위에 제목 줄이 있어서 머리글이 밀릴 때, 전각 숫자·비분리
공백·소프트 하이픈 때문에 찾기가 안 될 때, 같은 행이 두 번 들어왔을 때 — 를
한 줄 명령으로 처리합니다. 표준 라이브러리만 쓰므로 `pip install` 없이 바로
돌아가고, 파일은 밖으로 나가지 않습니다.

```bash
python -m kcsvlite inspect 1월고객.csv
python -m kcsvlite clean 1월고객.csv -o 1월고객_clean.csv --dedupe
```

- 바꾼 내용을 단계별로 출력하고, 결과 옆에 변경 내역을 남깁니다.
- 읽을 때 머리글을 임의로 정하지 않습니다(원본 그대로 격자로 읽고 판단).
- 없는 값은 빈 값으로 둡니다(없는 것과 0은 다릅니다).
- `.xlsx`·파일 합치기·분할·전화번호/날짜/금액 정규화·주민번호 가리기는
  [풀버전](https://psgfanatic8.gumroad.com/l/korean-csv-excel-cleaner-batch-processor)에 있습니다.

## License

MIT © 2026 Seonggyu Park — use it at work, in a client project, inside your own
product. No attribution needed.
