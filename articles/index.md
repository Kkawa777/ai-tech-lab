---
layout: default
title: 記事一覧
permalink: /articles/
---

# 記事一覧

{% assign ready_articles = site.articles | where: "status", "ready" | sort: "order" %}
<div class="article-grid">
{% for article in ready_articles %}
  <a class="article-card" href="{{ article.permalink | relative_url }}">
    {% if article.image.path %}
    <img class="article-card-thumb" src="{{ article.image.path | relative_url }}" alt="{{ article.image.alt | default: article.title }}">
    {% else %}
    <span class="article-card-thumb article-card-thumb--placeholder">{{ article.category | slice: 0, 1 }}</span>
    {% endif %}
    <span class="article-card-body">
      <span class="article-card-badges">
        {% if article.category %}<span class="badge badge-category">{{ article.category }}</span>{% endif %}
        {% if article.difficulty %}<span class="badge badge-difficulty">{{ article.difficulty }}</span>{% endif %}
      </span>
      <span class="article-card-title">{{ article.title }}</span>
      {% if article.estimated_time %}<span class="article-card-time">{{ article.estimated_time }}</span>{% endif %}
    </span>
  </a>
{% endfor %}
</div>
