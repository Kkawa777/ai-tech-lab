---
layout: home
title: ホーム
---
<section class="hero">
  <h1 class="hero-title">{{ site.title | escape }}</h1>
  <p class="hero-tagline">{{ site.tagline | escape }}</p>
  <p class="hero-description">{{ site.description | escape }}</p>
  <div class="pillar-cards">
    <span class="pillar-card">Arduino入門</span>
    <span class="pillar-card">ESP8266 / IoT</span>
    <span class="pillar-card">AI×電子工作</span>
    <span class="pillar-card">購入ガイド</span>
  </div>
</section>

<section class="home-featured">
  <h2>はじめての方はこちら</h2>
  {% assign featured = site.articles | where: "status", "ready" | sort: "order" | first %}
  {% if featured %}
  <div class="article-grid">
    <a class="article-card" href="{{ featured.permalink | relative_url }}">
      {% if featured.image.path %}
      <img class="article-card-thumb" src="{{ featured.image.path | relative_url }}" alt="{{ featured.image.alt | default: featured.title }}" width="1200" height="630">
      {% else %}
      <span class="article-card-thumb article-card-thumb--placeholder">{{ featured.category | slice: 0, 1 }}</span>
      {% endif %}
      <span class="article-card-body">
        {% if featured.category %}<span class="badge badge-category">{{ featured.category }}</span>{% endif %}
        <span class="article-card-title">{{ featured.title }}</span>
      </span>
    </a>
  </div>
  {% endif %}
  <p><a href="{{ "/articles/" | relative_url }}">記事一覧を見る</a></p>
</section>
