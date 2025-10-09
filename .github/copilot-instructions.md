---
applyTo: 'docs/**'
---

- translation.xmlはXLIFF 2.1ファイルです
  - XLIFFの仕様は次のページに記載があります https://docs.oasis-open.org/xliff/xliff-core/v2.1/xliff-core-v2.1.html
- src.txtが原語、tgt.txtが訳出です
- 翻訳にあたって、用語集は "context/glossary.tsv" を参照してください
- 翻訳に際して新しい用語を見つけた場合は"context/glossary.tsv"に追加してください
- 翻訳で気になった箇所があれば、translation.xmlのXLIFF上に`<note>`でコメントを残してください