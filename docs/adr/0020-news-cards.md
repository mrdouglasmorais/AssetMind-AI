# ADR 0020 — News cards

Status: accepted

Context: Headlines are title, publisher, date, and link. The Google News RSS search used here does not attach a photo to each item. Opening the article to read an image would leave the allowed host and copy page content.

Decision: The chat renders up to three headlines as a horizontal card row. An https image is shown only when that feed item declares one in `media:content`, `media:thumbnail`, or an `img` in the item description. Otherwise the card draws a local illustration. The article URL is not requested. The same item list is fenced as `assetmind-news` so the narrator copies it unchanged.

Alternatives: Scrape each article for `og:image`, or show one channel logo on every card.

Consequences: A card without a feed image is visibly an illustration. Tests parse a fixture feed and do not call Google.
