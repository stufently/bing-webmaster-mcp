# Bing Webmaster Tools API surface

Transcribed from Microsoft's `IWebmasterApi` interface reference and each method's
definition page, fetched 2026-08-25. The interface has 62 methods. Exactly three are
marked `Obsolete` by Microsoft and are documented but deliberately not exposed, leaving
59 supported methods. HTTP verbs come from each method's `WebGet` or `WebInvoke`
attribute. R/W is this project's safety classification; `FetchUrl` is a write because it
requests a crawl and consumes quota.

Primary source: <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi?view=bing-webmaster-dotnet>

<!-- method-count: 62 -->
<!-- supported-count: 59 -->

| Method | Params | HTTP | R/W | Group |
|---|---|---|---|---|
| `GetUserSites` | — | GET | R | Sites |
| `GetSiteRoles` | siteUrl, includeAllSubdomains | GET | R | Sites |
| `GetSiteMoves` | siteUrl | GET | R | Sites |
| `AddSite` | siteUrl | POST | W | Sites |
| `RemoveSite` | siteUrl | POST | W | Sites |
| `VerifySite` | siteUrl | POST | W | Sites |
| `AddSiteRoles` | siteUrl, delegatedUrl, userEmail, authenticationCode, isAdministrator, isReadOnly | POST | W | Sites |
| `RemoveSiteRole` | siteUrl, siteRole: SiteRoles | POST | W | Sites |
| `SubmitSiteMove` | siteUrl, settings: SiteMoveSettings | POST | W | Sites |
| `GetQueryStats` | siteUrl | GET | R | Traffic |
| `GetQueryTrafficStats` | siteUrl, query | GET | R | Traffic |
| `GetQueryPageStats` | siteUrl, query | GET | R | Traffic |
| `GetQueryPageDetailStats` | siteUrl, query, page | GET | R | Traffic |
| `GetPageStats` | siteUrl | GET | R | Traffic |
| `GetPageQueryStats` | siteUrl, page | GET | R | Traffic |
| `GetRankAndTrafficStats` | siteUrl | GET | R | Traffic |
| `GetUrlInfo` | siteUrl, url | GET | R | Crawl |
| `GetUrlTrafficInfo` | siteUrl, url | GET | R | Crawl |
| `GetChildrenUrlInfo` | siteUrl, url, page, filterProperties: FilterProperties | POST | R | Crawl |
| `GetChildrenUrlTrafficInfo` | siteUrl, url, page | GET | R | Crawl |
| `GetCrawlStats` | siteUrl | GET | R | Crawl |
| `GetCrawlIssues` | siteUrl | GET | R | Crawl |
| `GetCrawlSettings` | siteUrl | GET | R | Crawl |
| `GetFetchedUrls` | siteUrl | GET | R | Crawl |
| `GetFetchedUrlDetails` | siteUrl, url | GET | R | Crawl |
| `SaveCrawlSettings` | siteUrl, crawlSettings: CrawlSettings | POST | W | Crawl |
| `FetchUrl` | siteUrl, url | POST | W | Crawl |
| `GetUrlSubmissionQuota` | siteUrl | GET | R | Submission |
| `SubmitUrl` | siteUrl, url | POST | W | Submission |
| `SubmitUrlBatch` | siteUrl, urlList | POST | W | Submission |
| `GetContentSubmissionQuota` | siteUrl | GET | R | Content submission |
| `SubmitContent` | siteUrl, url, httpMessage, structuredData, dynamicServing | POST | W | Content submission |
| `GetFeeds` | siteUrl | GET | R | Sitemaps |
| `GetFeedDetails` | siteUrl, feedUrl | GET | R | Sitemaps |
| `SubmitFeed` | siteUrl, feedUrl | POST | W | Sitemaps |
| `RemoveFeed` | siteUrl, feedUrl | POST | W | Sitemaps |
| `GetBlockedUrls` | siteUrl | GET | R | URL blocking |
| `AddBlockedUrl` | siteUrl, blockedUrl: BlockedUrl | POST | W | URL blocking |
| `RemoveBlockedUrl` | siteUrl, blockedUrl: BlockedUrl | POST | W | URL blocking |
| `GetQueryParameters` | siteUrl | GET | R | Query parameters |
| `AddQueryParameter` | siteUrl, queryParameter | POST | W | Query parameters |
| `RemoveQueryParameter` | siteUrl, queryParameter | POST | W | Query parameters |
| `EnableDisableQueryParameter` | siteUrl, queryParameter, isEnabled | POST | W | Query parameters |
| `GetCountryRegionSettings` | siteUrl | GET | R | Geo targeting |
| `AddCountryRegionSettings` | siteUrl, settings: CountryRegionSettings | POST | W | Geo targeting |
| `RemoveCountryRegionSettings` | siteUrl, settings: CountryRegionSettings | POST | W | Geo targeting |
| `GetActivePagePreviewBlocks` | siteUrl | GET | R | Page preview blocks |
| `AddPagePreviewBlock` | siteUrl, url, reason: BlockReason | POST | W | Page preview blocks |
| `RemovePagePreviewBlock` | siteUrl, url | POST | W | Page preview blocks |
| `GetDeepLinkBlocks` | siteUrl | GET | R | Deep link blocks |
| `AddDeepLinkBlock` | siteUrl, market, searchUrl, deepLinkUrl | POST | W | Deep link blocks |
| `RemoveDeepLinkBlock` | siteUrl, market, searchUrl, deepLinkUrl | POST | W | Deep link blocks |
| `GetLinkCounts` | siteUrl, page | GET | R | Inbound links |
| `GetUrlLinks` | siteUrl, link, page | GET | R | Inbound links |
| `GetConnectedPages` | siteUrl | GET | R | Inbound links |
| `AddConnectedPage` | siteUrl, masterUrl | POST | W | Inbound links |
| `GetKeyword` | q, country, language, startDate, endDate | GET | R | Keywords |
| `GetKeywordStats` | q, country, language | GET | R | Keywords |
| `GetRelatedKeywords` | q, country, language, startDate, endDate | GET | R | Keywords |
| `GetDeepLinkAlgoUrls` | siteUrl | GET | R | Deep links obsolete |
| `GetDeepLink` | siteUrl, url | GET | R | Deep links obsolete |
| `UpdateDeepLink` | siteUrl, algoUrl, deepLink, weight | POST | W | Deep links obsolete |

## Deliberate exclusions

- `GetDeepLinkAlgoUrls` — Excluded: Microsoft marks this method `Obsolete`.
- `GetDeepLink` — Excluded: Microsoft marks this method `Obsolete`.
- `UpdateDeepLink` — Excluded: Microsoft marks this method `Obsolete`.

## Verified complex request types

The exact serialized property names below come from the linked Microsoft type and
property pages. Enum-valued properties are represented by their JSON numeric value;
callers must not invent enum names.

- `BlockedUrl`: `Date`, `DaysToExpire`, `EntityType`, `RequestType`, `Url`.
- `CrawlSettings`: `CrawlBoostAvailable`, `CrawlBoostEnabled`, `CrawlRate`.
- `FilterProperties`: `CrawlDateFilter`, `DiscoveredDateFilter`, `DocFlagsFilters`,
  `HttpCodeFilters`.
- `SiteMoveSettings`: `Date`, `MoveScope`, `MoveType`, `SourceUrl`, `TargetUrl`.
- `CountryRegionSettings`: `Date`, `TwoLetterIsoCountryCode`, `Type`, `Url`.
- `SiteRoles`: `Date`, `DelegatedCode`, `DelegatedCodeOwnerEmail`, `DelegatorEmail`,
  `Email`, `Expired`, `Role`, `Site`, `VerificationSite`.

`SubmitContent` takes an RFC-style HTTP response and structured data as base64 strings;
`dynamicServing` is an integer from 0 through 5. `SubmitUrlBatch` has a documented
per-call cap of 500 and must also fit the live quota returned by
`GetUrlSubmissionQuota`. Microsoft documents a 10 MB uncompressed content payload limit
per `SubmitContent` request; the combined decoded `httpMessage` and `structuredData`
must fit it.

## Verified response types

- `Site` (returned by `GetUserSites`): `AuthenticationCode`, `DnsVerificationCode`,
  `IsVerified`, `Url`. Source:
  <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.site?view=bing-webmaster-dotnet>,
  fetched 2026-09-02. The first two are the ownership proofs a site must publish in its
  verification file or meta tag and in a DNS TXT record; anyone holding one can claim the
  site in another Bing account. `SiteRoles.DelegatedCode` is the same kind of value —
  Microsoft's `AddSiteRoles` takes it as `authenticationCode`. All three are redacted in
  every response this project returns; see `docs/operations.md`.
- `UrlWithCrawlIssues` (returned by `GetCrawlIssues`): `HttpCode` (Int32), `InLinks`,
  `Issues`, `Url`. Source:
  <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.urlwithcrawlissues?view=bing-webmaster-dotnet>,
  fetched 2026-09-01.
- `UrlWithCrawlIssues.CrawlIssues` is a `[Flags]` enum, so `Issues` is a bitmask and one
  URL can carry several: `None` 0, `Code301` 1, `Code302` 2, `Code4xx` 4, `Code5xx` 8,
  `BlockedByRobotsTxt` 16, `ContainsMalware` 32, `ImportantUrlBlockedByRobotsTxt` 64,
  `DnsErrors` 128, `TimeOutErrors` 256. Source:
  <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.urlwithcrawlissues.crawlissues?view=bing-webmaster-dotnet>,
  fetched 2026-09-01. There is no `noindex` member and no separate 404 or 403 member;
  the exact status code is the `HttpCode` field, not a flag. This project therefore
  derives `http_404` and `http_403` from `HttpCode` on rows Bing itself flagged
  `Code4xx`, and derives no `noindex` category from anything.

- `UrlInfo` (returned by `GetUrlInfo`): `AnchorCount`, `DiscoveryDate`, `DocumentSize`,
  `HttpStatus`, `IsPage`, `LastCrawledDate`, `TotalChildUrlCount`, `Url`. Source:
  <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.urlinfo?view=bing-webmaster-dotnet>,
  fetched 2026-09-01. There is no indexing-status, robots-directive or content-changed
  property.
  `HttpStatus` is an `Int32` and Microsoft documents no sentinel for it. **Observed on a
  live account, 2026-09-02:** `GetUrlInfo` returned `HttpStatus: 0` with `IsPage: true`
  and a `LastCrawledDate` for a URL that answers 404 today. Zero is not a status code, so
  this project reads it as "Bing reported no status" and labels the row
  `http_status_reported: false` rather than passing a number a caller would read as one.
  Nothing is derived: the raw `HttpStatus` is kept, and the real status is not fetched.
- **Empty responses, observed on a live account, 2026-09-02.** For the same site and in
  the same minute, `GetLinkCounts` returned `{"Links": [], "TotalPages": 0}`,
  `GetCrawlIssues` returned `[]` and `GetFetchedUrls` returned `[]`, while `GetCrawlStats`
  reported `InLinks: 1700`, `CrawlErrors: 4` and `Code4xx: 1`. Microsoft documents no way
  to distinguish "nothing to report" from "not reported"; there is no status field, no
  coverage flag and no error. The reads therefore label an empty response instead of
  presenting it as a measurement.
- `QueryStats` (returned by `GetQueryStats`): `AvgClickPosition`,
  `AvgImpressionPosition`, `Clicks`, `Date`, `Impressions`, `Query`.
  `RankAndTrafficStats` (returned by `GetRankAndTrafficStats`): `Clicks`, `Date`,
  `Impressions`. Sources:
  <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.querystats?view=bing-webmaster-dotnet>
  and
  <https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.rankandtrafficstats?view=bing-webmaster-dotnet>,
  fetched 2026-09-01. **Bing returns no CTR field**; a click-through rate is
  `Clicks / Impressions`, computed by the caller.

Microsoft's `AddSiteRoles` JSON example pairs `siteUrl: http://example.com` with
`delegatedUrl: http://host1.example.com`. The delegated URL is therefore validated as
absolute but is not restricted to the site's exact host.
