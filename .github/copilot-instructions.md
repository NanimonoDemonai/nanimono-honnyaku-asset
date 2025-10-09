---
applyTo: 'docs/**'
---

- translation.xmlはXLIFF 2.1ファイルです
  - XLIFFの仕様は次のページに記載があります https://docs.oasis-open.org/xliff/xliff-core/v2.1/xliff-core-v2.1.html
- src.txtが原語、tgt.txtが訳出です
- 翻訳にあたって、用語集は "context/glossary.tsv" を参照してください
- 翻訳に際して新しい用語を見つけた場合は"context/glossary.tsv"に追加してください
- 翻訳で気になった箇所があれば、translation.xmlのXLIFF上に`<note>`でコメントを残してください
- 別の訳例を示したいならば<meta>を使ってください
```マークアップの例
<unit id="2">
  <segment>
    <source>Submit</source>
    <target>送信</target>
    <meta type="alternate-translation" key="1">提出</meta>
    <meta type="alternate-translation" key="2">登録</meta>
  </segment>
</unit>
```