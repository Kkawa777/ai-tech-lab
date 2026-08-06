---
layout: home
title: ホーム
---

# {{ site.title }}

{{ site.description }}

## はじめての方はこちら

{% assign featured = site.articles | where: "status", "ready" | sort: "order" | first %}
{% if featured %}
### [{{ featured.title }}]({{ featured.permalink | relative_url }})
{% endif %}

[記事一覧を見る]({{ "/articles/" | relative_url }})
