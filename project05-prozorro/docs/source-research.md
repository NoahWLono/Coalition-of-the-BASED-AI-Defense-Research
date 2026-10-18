# Source and access research

Observed on 17 October 2026 in America/Toronto. UTC acquisition timestamps, HTTP results, response byte counts and SHA-256 hashes are in `source-acquisition-ledger.json`. This research step fetched official documentation and inspected the public website. It did not import procurement records. Documentation hashes identify the responses read; their full bodies are not retained.

## Access and reuse

The [official Prozorro developer page](https://prozorro.gov.ua/openprocurement) returned HTTP 200 through an ordinary unauthenticated GET. Its open-data statement permits copying, publication, distribution and use of public open data, including commercial use and inclusion in another product, with mandatory source attribution. This is the observed reuse statement; this project does not assert a particular Creative Commons or SPDX license. Attribute Prozorro beside every exported record and retain its public source URL and acquisition date. The statement does not authorize access to hidden fields or remove independent privacy restrictions.

The web search tool initially received HTTP 503 for the same page. A subsequent ordinary Python urllib GET succeeded, with no credentials, proxy changes or access-control workarounds. The two observations describe different requests. The official developer page links the [current API documentation](https://prozorro-api-docs.readthedocs.io/uk/latest/index.html).

The user's [starting documentation](https://api-docs.openprocurement.org/en/latest/) identifies itself as `openprocurement.api 2.4.18`. The official linked documentation identifies API `2.5`. A live GET of [the deployed OpenAPI specification](https://public-api.prozorro.gov.ua/api/2.5/doc/spec) returned `info.version = 2.7.47` and title `Prozorro CDB API`. These are three different version observations. The URL's API version and the application's release version must not be conflated. A search-engine index showed an older deployed version, `2.7.42.2`; the ledger uses the live result.

Some read-only GET requests require no authentication, according to the [authentication documentation](https://prozorro-api-docs.readthedocs.io/uk/master/basic-actions/authentication.html). This prototype needs no broker credentials. Stop a path on an access denial rather than requesting elevated access.

## Feed behavior and a bounded discovery route

The [feed documentation](https://prozorro-api-docs.readthedocs.io/uk/master/basic-actions/feed.html) specifies cursor pagination using `public_modified`, not the displayed `dateModified`. It returns `id` and `dateModified` by default. Follow the returned `next_page` cursor without inventing offsets. The default page size is 100 and the maximum is 1000. Test objects and draft records are excluded by default. The documented public endpoint ceiling is 140 requests per second; that ceiling is not a recommended project workload. No category or publication-date filter appears in this feed specification. An empty forward page means the current feed end; a missing backward next page means the backward end.

The [optional-fields specification](https://prozorro-api-docs.readthedocs.io/uk/master/basic-actions/opt_fields.html) lists supported tender fields such as `status`, `dateCreated`, `tenderID`, `lots`, `contracts`, `procuringEntity` and `procurementMethodType`. It does not list `title`, `items` or classification for the tender feed. Scanning an entire national feed to find fifty historical paper purchases would exceed this prototype's modest acquisition needs.

The [official public search](https://prozorro.gov.ua/uk/search/tender?text=%D0%9F%D0%B0%D0%BF%D1%96%D1%80+%D0%904&notice.start=2025-01-01&notice.end=2025-03-31) was exercised through its visible controls with search text `Папір А4` and publication dates 2025-01-01 through 2025-03-31. The resulting URL retained those exact parameters and the UI reported 926 results, twenty cards per page. This is a discovery count, not a count of usable civilian lots. The results include defense buyers, mixed goods and cancellations. Skip those records before fetching their details. Do not save defense search cards or their locations in the demonstration dataset.

The website's date chip rendered each entered date one day earlier in this Toronto browser, while the ISO input values and resulting query URL retained the chosen dates. Therefore inspect each source publication or creation date and enforce the reporting window in the importer. A UI count does not establish a population frame.

One visibly civilian result, [education department paper purchase UA-2025-03-14-012026-a](https://prozorro.gov.ua/uk/tender/UA-2025-03-14-012026-a), exposes a normal rendered link to [its public API record](https://public-api.prozorro.gov.ua/api/2.5/tenders/ca468e743a754ab49772db5f52c8cbe6). The link supplies the API UUID without inspecting hidden application state or an undocumented search API. Other civilian search candidates were `UA-2025-03-18-008846-a`, `UA-2025-02-14-003379-a` and `UA-2025-02-21-003920-a`. These are discovery candidates, not reviewed comparison records.

Recommended acquisition procedure, as a project choice: use the visible public search; retain candidate ID, title and civilian-screen decision; open accepted pages and follow their published public API links; fetch sequentially at no more than one request per second; cap candidates, bytes and retries; stop when fifty usable lots are obtained or the explicit cap is reached. Follow public document links only when necessary for terms and only after privacy screening. No broad synchronization, hidden-field reconstruction or authenticated endpoint is needed.

The [rate-control documentation](https://prozorro-api-docs.readthedocs.io/uk/master/basic-actions/performance.html) says HTTP 429 responses require increasing the interval between requests. Honor `Retry-After` when supplied and use a bounded retry policy. Do not treat the absence of 429 as permission for unbounded traffic.

## Identifiers, stages and dates

The [Tender schema](https://prozorro-api-docs.readthedocs.io/uk/master/standard/tender.html) distinguishes the paper-facing `tenderID` from API `id`. `dateCreated` denotes creation; `dateModified` denotes modification. Preserve these separately from document `datePublished`, award dates, contract signing and acquisition timestamps. The tender's `value` is an estimated value. A historical reporting window must declare its chosen date basis and must not silently use the feed modification order as publication order.

The [Contract schema](https://prozorro-api-docs.readthedocs.io/uk/master/standard/contract.html) carries `id`, `awardID`, status, value and signing date. Contracting records can add `changes`, `amountPaid` and implementation data. `amountPaid` is the recorded paid amount and belongs in a separate stage. Its absence is unknown. An amended contract or an award is not a second purchase. Preserve identifiers sufficient to join the tender, lot, award and contract.

The [value definitions](https://prozorro-api-docs.readthedocs.io/uk/master/standard/util.html) distinguish amount, ISO currency, `valueAddedTaxIncluded` and, for contract values, optional `amountNet`. An explicit false tax flag differs from an absent flag. Do not impute a tax rate or derive net amounts without evidence.

## Redactions and privacy

The [restricted-access documentation](https://prozorro-api-docs.readthedocs.io/en/latest/tendering/config/restricted.html) documents a `restricted` boolean and masked fields. Masking may replace descriptions with a hidden marker, quantities and coordinates with zero, delivery dates with an epoch-like date, and document titles or URLs with a hidden marker. A zero quantity in such a record is not evidence of a real zero purchase. Exclude restricted records from comparison and preserve a restriction reason. Never reconstruct the masked value.

The [ConfidentialDocument schema](https://prozorro-api-docs.readthedocs.io/uk/master/standard/confidentialdocument.html) distinguishes `public` from `buyerOnly` and records a confidentiality rationale. The [limited-procedure tutorial](https://prozorro-api-docs.readthedocs.io/en/latest/tendering/limited/tutorial.html) illustrates contract annexes withheld under wartime rules and forbidden downloads for nonowners. Its examples are schema demonstrations, not acquisitions or independent legal advice. Treat an absent public document as unavailable evidence. Retain permitted references and the exclusion reason.

The prototype should retain goods, quantities, fiscal terms and non-sensitive delivery conditions. Personal contacts, bank details, signatures, addresses and coordinates are unnecessary for this comparison and should not enter its outputs. Civilian status must be checked independently of the paper category because defense buyers also purchase ordinary paper.

## Currency and limits of this research

Use UAH-only groups initially and record `FX conversion: none`. The [NBU English API guide](https://bank.gov.ua/admin_uploads/article/Instr_API_KURS_VAL_Full_eng.pdf) is an official optional reference whose search-index text documents date and currency parameters. Direct retrieval returned HTTP 403 in this session, and no exchange-rate observation was acquired. A future cross-currency extension must verify the live interface and date semantics, record the original value and rate, and keep conversion sensitivity separate. Do not claim an NBU rate was used here.

All annotations in this note were produced by the assistant. They are source interpretations and acquisition guidance, not qualified human review, procurement legality findings or an evaluation of screening accuracy. No license uncertainty is being treated as permission: the dataset route relies on the explicit current Prozorro open-data statement and source attribution, while this ledger keeps documentation references and hashes.
