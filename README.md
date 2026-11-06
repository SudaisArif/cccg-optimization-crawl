# CCCG optimization-bound crawl

A small reproducible survey of CCCG papers whose running times might improve when an old optimization subroutine is replaced. The script collects leads; mathematical review determines whether a replacement is valid.

## Run it

Requires Python 3.10+, `curl`, and Poppler's `pdftotext`. There are no Python package dependencies.

```sh
python3 -m unittest -v test_crawl.py
python3 crawl.py --years 2005 2006 2007 --delay 1
```

The crawler checks `robots.txt`, waits at least one second between network requests by default, discovers same-host links in the selected years of the CCCG archive, and caches downloads in `.cache/`. Standard HTTPS redirects are followed. Repeated runs reuse cached PDFs, indexes, and available crawl rules. To refresh the archive, supply a new cache directory, for example `--cache .cache/refresh-2026-12`; cached content does not expire automatically. `--max-documents 10` makes a bounded test run; the manifest explicitly marks truncated coverage. A missing `robots.txt` (HTTP 404) permits the bounded crawl; other retrieval failures stop the run. Newer years sometimes provide one proceedings volume rather than individual papers; those are labeled `proceedings_volume`, not counted as individual papers.

## What the initial run found

The public archive was scanned on November 6, 2026 for **2005–2007**:

| Measure | Count |
| --- | ---: |
| Linked PDF documents | 217 |
| Bibliographic groups after merging short/full versions | 191 |
| Documents with usable extracted text | 213 |
| Extraction failures | 4 |
| Documents with optimization keywords | 25 |
| Distinct bibliographic groups with keyword hits | 20 |
| Leads manually reviewed | 5 |
| Checked applications of a modern theorem | 2, with stated scope |

This covers the links exposed by those three archive indexes, including invited material and full versions. It is not a scan of all CCCG years or a claim that every relevant result was found. The original fetch timestamps and SHA-256 hashes are in the manifest; its latest run timestamp records regeneration using the cache.

## Reviewed results

| Paper | Finding |
| --- | --- |
| [Shortest Descending Paths through Given Faces (2006)](https://cccg.ca/proceedings/2006/cccg10.pdf) | The fixed-face problem has constant-dimensional local blocks joined along a path. Dong--Lee--Ye's Theorem 1.3 gives expected nearly linear arithmetic/oracle time, retaining conditioning and precision logarithms. |
| [Touring Convex Bodies (2005)](https://cccg.ca/proceedings/2005/78.pdf) | The same argument applies to the base ordered tour through line segments in fixed dimension. This is a restricted family within the paper's more general formulation. |
| [Streaming Minimum Enclosing Balls (2006)](https://cccg.ca/proceedings/2006/cccg36.pdf) | The LP hit was a reference, not an established replaceable solver bottleneck. |
| [Kinetic MaxCut (2007)](https://cccg.ca/proceedings/2007/07a4.pdf) | The SDP hit was a reference. No new kinetic bound was established. |
| [Approximate Shortest Descent Path on a Terrain (2007)](https://cccg.ca/proceedings/2007/08b1full.pdf) | It cites convex optimization as prior work; its own method uses discretization and graph search. No automatic global bound update follows. |

For the two checked applications, the precise expected bound is

`O~(k log(R/r) log(R/(r delta)))`,

for additive error `delta ||c||_2 R`, where `R` bounds the product-domain diameter and `r` is an interior radius after removing forced equalities. Under controlled geometric/accuracy scales this simplifies to nearly linear time in `k`. These are applications of a known theorem, not claimed new optimization algorithms or geometry-independent strongly polynomial bounds. See the [full descending-path derivation](docs/descending-path-bound.md), including feasibility, degeneracies, and relative-error conversion.

## Files

- `crawl.py`: discovery, cached download, PDF extraction, keyword triage, and exports.
- `results/manifest.json`: every URL, status, metadata, original fetch time, hash, and extraction error.
- `results/papers.json`: bibliographic grouping of document versions.
- `results/candidates.csv`: document-level leads, including distinct versions.
- `results/litchikin.json`: grouped leads in the course's [LITchikin 1.4 catalog format](https://github.com/rpeng233/LITchikin/blob/main/open_problem_record.schema.json).
- `results/reviewed.json`: separately maintained manual judgments and applicable bounds.
- `docs/descending-path-bound.md`: the checked mathematical reduction.

The catalog intentionally keeps automatic leads marked `candidate_unreviewed`; manual results are separate so rerunning the crawler cannot overwrite them. Titles and author strings come from the archive indexes and can inherit imperfect mathematical markup.

## Limits

Keyword matching can miss relevant work and can pick up bibliography mentions, especially in two-column PDFs. Standalone reference headings are stripped when recognizable. Geometric phrases such as “interior point of a triangle” are not treated as interior-point solvers. A match is not evidence of an improvement: the number of variables, block dimensions, constraints, conditioning, approximation guarantee, and other algorithmic bottlenecks all need review.

Four PDFs could not be extracted: one has an invalid page count and three lack usable text layers. They remain explicitly listed in the manifest. Downloaded PDFs and full extracted texts stay in the ignored local cache; this repository publishes code, metadata, derived analysis, and links.

The crawl does not search citation databases, implement the theoretical optimizers, prove novelty, or run on a recurring schedule. It supplies a repeatable starting point for the literature review.
