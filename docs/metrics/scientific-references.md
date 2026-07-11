# Scientific References

Reference list for the scientific and standards basis behind LucidUI's metrics. See [metric-catalog.md](metric-catalog.md) for where each reference is used. Where full bibliographic detail is uncertain, this is marked with a TODO rather than guessed — see [CLAUDE.md](../../CLAUDE.md) ("do not invent implementation details").

## WCAG 2.1 Contrast Guidance

World Wide Web Consortium (W3C), "Web Content Accessibility Guidelines (WCAG) 2.1," Success Criterion 1.4.3 (Contrast Minimum). Used for the 4.5:1 normal-text contrast reference threshold in the [Contrast](metric-catalog.md#contrast) metric.

TODO: confirm exact W3C recommendation URL and publication date to cite precisely.

## Hick's Law

Hick, W. E. (1952). "On the rate of gain of information." *Quarterly Journal of Experimental Psychology*, 4(1), 11–26. Used as the basis for the [Hick's Law Estimate](metric-catalog.md#hicks-law-estimate) metric.

## Fitts's Law

Fitts, P. M. (1954). "The information capacity of the human motor system in controlling the amplitude of movement." *Journal of Experimental Psychology*, 47(6), 381–391. Used as the basis for the [Fitts's Law Index of Difficulty](metric-catalog.md#fittss-law-index-of-difficulty) metric.

## Miller's Law

Miller, G. A. (1956). "The magical number seven, plus or minus two: Some limits on our capacity for processing information." *Psychological Review*, 63(2), 81–97. Referenced only as historical context for the [Estimated Group Count](metric-catalog.md#estimated-group-count) metric — not used as a target or ideal UI grouping number.

## Rosenholtz, Li, and Nakano — Visual Clutter

Rosenholtz, R., Li, Y., & Nakano, L. (2007). "Measuring visual clutter." *Journal of Vision*, 7(2), 17. Used as the conceptual basis for the [Edge Density](metric-catalog.md#edge-density) clutter proxy.

TODO: confirm this is the correct/primary paper for the specific clutter formulation LucidUI implements, versus other Rosenholtz clutter-measurement publications (e.g. Feature Congestion, Subband Entropy).

## Hasler and Süsstrunk — Colorfulness

Hasler, D., & Süsstrunk, S. (2003). "Measuring colorfulness in natural images." *Proceedings of SPIE, Human Vision and Electronic Imaging VIII*, Vol. 5007. Used as the basis for the [Colorfulness](metric-catalog.md#colorfulness) metric.

## UIClip

UIClip is used as an independent, pretrained vision-language evaluator for UI screenshots.

TODO: add the exact UIClip paper title, authors, venue, and publication year, and a link to the official project/code repository, once confirmed. Do not implement or document integration details beyond what is confirmed from the primary source — see [docs/research/uiclip-integration.md](../research/uiclip-integration.md).
