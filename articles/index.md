---
layout: default
title: 記事一覧
permalink: /articles/
---

# 記事一覧

{% assign ready_articles = site.articles | where: "status", "ready" | sort: "order" %}
<ul>
{% for article in ready_articles %}
  <li><a href="{{ article.permalink | relative_url }}">{{ article.title }}</a></li>
{% endfor %}
</ul>
