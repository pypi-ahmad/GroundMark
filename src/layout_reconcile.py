"""Offline V3 geometry conversion and authoritative, non-transcribing matching.

These local models are never Sol response schemas. No inference, file I/O, or
parser wiring occurs here; see docs/LAYOUT-V3.md for the uncalibrated policy.
"""
from __future__ import annotations

from collections import defaultdict
import json
import math

# Re-export the existing local metadata API; artifact ownership is in layout.
from src.layout import (
    BBox, ParsePage, Point, _LayoutMetadata as _Metadata, NormalizedLayoutRegion,
    NormalizedLayoutPage, ReconcilePolicy, MatchEvidence, BlockDecision, ReconciliationMetadata,
)
from src.layout_detector import LABELS, LayoutPageResult

ROLE_HINTS = dict.fromkeys(LABELS, "text") | {
    "doc_title": "title", "paragraph_title": "heading", "table": "table",
    **dict.fromkeys(("chart", "image", "header_image", "footer_image", "seal"), "figure"),
    "header": "page_header", "footer": "page_footer",
    **dict.fromkeys(("aside_text", "footnote", "vision_footnote"), "marginalia"),
}

TEXT_TYPES = frozenset(("title", "heading", "text", "list", "key_value", "marginalia",
                        "other", "page_header", "page_footer"))
CLASS_COMPATIBILITY = {
    **dict.fromkeys(("text", "content", "abstract", "algorithm", "reference_content", "vertical_text"), TEXT_TYPES),
    **dict.fromkeys(("doc_title", "paragraph_title"), frozenset(("title", "heading", "text", "other"))),
    **dict.fromkeys(("display_formula", "inline_formula", "formula_number", "number"), frozenset(("text", "key_value", "other"))),
    **dict.fromkeys(("figure_title", "reference"), frozenset(("text", "heading", "other"))),
    **dict.fromkeys(("aside_text", "footnote", "vision_footnote"), frozenset(("marginalia", "text", "list", "key_value", "other"))),
    "header": frozenset(("page_header", "text", "marginalia", "key_value", "other")),
    "footer": frozenset(("page_footer", "text", "marginalia", "key_value", "other")),
    **dict.fromkeys(("chart", "image", "header_image", "footer_image", "seal"), frozenset(("figure",))),
    "table": frozenset(("table",)),
}


class ReconciliationInvariantError(RuntimeError):
    """Application defect, never an ordinary detector miss."""


class LayoutConversionError(ValueError):
    """Safe failure with no source text or native/provider exception details."""
    def __init__(self, code: str, *, page: int, region_index: int | None = None):
        self.code, self.page, self.region_index = code, page, region_index
        super().__init__(f"V3 conversion failed ({code}); page={page}, region={region_index}.")


class ReconciliationResult(_Metadata):
    page: ParsePage
    metadata: ReconciliationMetadata


def layout_match_counts(artifact):
    """Safe display counts, not transcription or raw detector labels."""
    details = artifact.reconciliation if artifact is not None else None
    return {
        "regions": len(artifact.layout.regions) if artifact is not None else None,
        "matches": sum(d.region_index is not None for d in details.decisions) if details else None,
        "unmatched_blocks": sum(d.region_index is None for d in details.decisions) if details else None,
        "unmatched_regions": len(details.unmatched_region_indices) if details else None,
        "review_blocks": sum(bool(d.reasons or d.review_flags) for d in details.decisions) if details else None,
        **{f"accepted_{flag}": sum(d.region_index is not None and flag in d.review_flags
                                  for d in details.decisions) if details else None
           for flag in ("split", "merge", "many_to_many", "contour_fallback")},
    }


def layout_inspection_summary(artifact, diagnostic):
    """One content-free summary for progress and saved-result inspection."""
    from src.layout_detector import MODEL_ID, REVISION
    from src.diagnostics import safe_identifier
    layout = artifact.layout if artifact else None
    return dict(
        page=diagnostic.page, model_id=safe_identifier(layout.model_id if layout else MODEL_ID),
        revision=safe_identifier(layout.revision if layout else REVISION),
        model_provenance="analysis" if layout else "configured",
        device=diagnostic.layout_device, layout_seconds=diagnostic.layout_seconds,
        page_seconds=diagnostic.page_seconds, layout_stage=diagnostic.layout_stage,
        layout_code=diagnostic.layout_code, layout_fallback=diagnostic.layout_fallback,
        application_error=diagnostic.application_error,
        fallback_reason=diagnostic.layout_fallback_reason,
        execution_failures=diagnostic.layout_execution_failures, **layout_match_counts(artifact),
    )


GIVEN_LAYOUT_MAX_BYTES = 64 * 1024
GIVEN_LAYOUT_MAX_REGIONS = 300


def _segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length)) if length else 0
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _simplified_contour(region, width, height, tolerance):
    """Closed RDP, with a conservative boundary bound including serialization."""
    points = [(x * width, y * height) for x, y in region.polygon]
    # Split a closed ring at its farthest vertex; avoid a zero-length chord.
    split = max(range(1, len(points)), key=lambda i: math.dist(points[0], points[i]))
    ring = points + points[:1]
    kept = {0, split, len(points)}
    stack = [(0, split), (split, len(points))]
    while stack:
        start, end = stack.pop()
        if end - start <= 1:
            continue
        index = max(range(start + 1, end), key=lambda i: _segment_distance(ring[i], ring[start], ring[end]))
        if _segment_distance(ring[index], ring[start], ring[end]) > tolerance:
            kept.add(index)
            stack.extend(((start, index), (index, end)))
    indices = sorted(kept)
    polygon = [(round(ring[i][0] / width, 6), round(ring[i][1] / height, 6)) for i in indices[:-1]]
    try:
        _validate_polygon(polygon)
        area = lambda p: sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1]))
        if area(polygon) * area(list(region.polygon)) <= 0:
            return None
        if any(not 0 <= value <= 1 for point in polygon for value in point):
            return None
        # Each original arc stays within a convex capsule around its chord.
        # Continuous projection also bounds the reverse chord-to-arc distance.
        deviation = max(_segment_distance(ring[i], ring[a], ring[b])
                        for a, b in zip(indices, indices[1:]) for i in range(a, b + 1))
        rounding = max(math.dist(ring[i], (x * width, y * height))
                       for i, (x, y) in zip(indices, polygon))
        bound = deviation + rounding
        if bound > 1:
            return None
        return polygon, bound
    except ValueError:
        return None


def project_layout_guide(layout: NormalizedLayoutPage):
    """Return bounded JSON and contour provenance; never modify source geometry."""
    from src.layout import GuideContour

    def dump(value):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=True, allow_nan=False)

    if len(layout.regions) > GIVEN_LAYOUT_MAX_REGIONS:
        raise LayoutConversionError("layout_prompt_too_large", page=layout.page)
    regions = sorted(layout.regions, key=lambda r: (r.order is None, r.order or 0, r.index))
    items = []
    records = []
    for region in regions:
        box = [fn(v * 1_000_000) / 1_000_000 for fn, v in zip(
            (math.floor, math.floor, math.ceil, math.ceil), region.bbox.xyxy)]
        items.append(dict(id=f"r{region.index:03d}", class_id=region.class_id,
                          label=LABELS[region.class_id], bbox=box, score=round(region.score, 4),
                          order=region.order, contour="omitted"))
        records.append(GuideContour(region_index=region.index, status="omitted", reason="budget_or_precision"))
    payload = dict(page=layout.page, coordinates="normalized_xyxy", regions=items)
    if len(dump(payload).encode("utf-8")) > GIVEN_LAYOUT_MAX_BYTES:
        raise LayoutConversionError("layout_prompt_too_large", page=layout.page)
    for index, (item, region) in enumerate(zip(items, regions)):
        if region.contour_status != "valid":
            records[index] = GuideContour(region_index=region.index, status="omitted", reason=region.contour_status)
            continue
        polygon = [(round(x, 6), round(y, 6)) for x, y in region.polygon]
        x0, y0, x1, y1 = region.bbox.xyxy
        rectangle = {(round(x, 6), round(y, 6)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))}
        if len(polygon) == 4 and set(polygon) == rectangle:
            records[index] = GuideContour(region_index=region.index, status="omitted", reason="redundant_box")
            continue
        candidates = [(polygon, "full", 0)]
        # Only simplify when the complete rounded contour cannot fit or validate.
        for tolerance in (None, .25, .5, 1.0):
            if tolerance is not None:
                simplified = _simplified_contour(region, layout.width_px, layout.height_px, tolerance)
                if simplified is None:
                    continue
                candidate, bound = simplified
                candidates = [(candidate, "simplified", bound)]
            candidate, status, bound = candidates[0]
            try:
                _validate_polygon(candidate)
            except ValueError:
                continue
            item.update(polygon_points=candidate, contour=status)
            if len(dump(payload).encode("utf-8")) <= GIVEN_LAYOUT_MAX_BYTES:
                records[index] = GuideContour(region_index=region.index, status=status, max_deviation_px=bound)
                break
            item.pop("polygon_points")
            item["contour"] = "omitted"
    return dump(payload), tuple(records)


def given_layout_json(layout: NormalizedLayoutPage) -> str:
    """Compatibility wrapper for the bounded guide text."""
    return project_layout_guide(layout)[0]


def _deduplicate(points):
    result = []
    for point in points:
        if not result or result[-1] != point:
            result.append(point)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p):
    return (_cross(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


def _intersects(a, b, c, d):
    ab_c, ab_d, cd_a, cd_b = _cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b)
    return (((ab_c < 0 < ab_d or ab_d < 0 < ab_c) and (cd_a < 0 < cd_b or cd_b < 0 < cd_a))
            or _on_segment(a, b, c) or _on_segment(a, b, d)
            or _on_segment(c, d, a) or _on_segment(c, d, b))


def _validate_polygon(points):
    if len(points) < 3 or len(set(points)) != len(points):
        raise ValueError("Degenerate polygon")
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    if not math.isfinite(area) or area == 0:
        raise ValueError("Degenerate polygon")
    # ponytail: quadratic contour validation; use a sweep line only if profiling warrants it.
    for i, a in enumerate(points):
        b, previous = points[(i + 1) % len(points)], points[i - 1]
        if _cross(previous, a, b) == 0 and sum((p - x) * (q - x) for p, x, q in zip(previous, a, b)) > 0:
            raise ValueError("Overlapping adjacent edges")
        for j in range(i + 1, len(points)):
            if j == i + 1 or (i == 0 and j == len(points) - 1):
                continue
            if _intersects(a, b, points[j], points[(j + 1) % len(points)]):
                raise ValueError("Self-intersecting polygon")


def _clip_to_box(points, box):
    # For area only, disconnected components may be joined by retraced boundary
    # edges. Their signed areas cancel; do not validate this walk as one contour.
    x0, y0, x1, y1 = box
    for axis, bound, lower in ((0, x0, True), (0, x1, False), (1, y0, True), (1, y1, False)):
        clipped = []
        for start, end in zip(points[-1:] + points[:-1], points):
            inside_start = start[axis] >= bound if lower else start[axis] <= bound
            inside_end = end[axis] >= bound if lower else end[axis] <= bound
            if inside_start != inside_end:
                t = (bound - start[axis]) / (end[axis] - start[axis])
                other = start[1 - axis] + t * (end[1 - axis] - start[1 - axis])
                clipped.append((bound, other) if axis == 0 else (other, bound))
            if inside_end:
                clipped.append(end)
        points = _deduplicate(clipped)
    return points


def _clip_polygon(points, width, height):
    points = _clip_to_box(points, (0, 0, width, height))
    _validate_polygon(points)
    return points


def _polygon_area(points):
    if len(points) < 3:
        return 0.0
    x, y = points[0]
    return abs(math.fsum((a[0] - x) * (b[1] - y) - (b[0] - x) * (a[1] - y)
                         for a, b in zip(points, points[1:] + points[:1]))) / 2


def _normalized_contour(raw, width, height):
    """Keep finite source points; unavailable contours never fabricate a ring."""
    if raw is None:
        return (), (), False, "missing"
    raw_points = ()
    try:
        if len(raw) == 0:
            return (), (), False, "missing"
        if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in raw):
            return (), (), False, "unusable"
        raw_points = tuple(tuple(p) for p in raw)
        points = _deduplicate(raw_points)
        _validate_polygon(points)
        clipped = _clip_polygon(points, width, height)
        polygon = tuple((x / width, y / height) for x, y in clipped)
        _validate_polygon(list(polygon))
        return raw_points, polygon, points != clipped, "valid"
    except (ValueError, TypeError, OverflowError, ZeroDivisionError):
        return raw_points, (), False, "unusable"


def convert_layout(result: LayoutPageResult) -> NormalizedLayoutPage:
    """Validate and normalize one runtime result without changing its pixels."""
    if any(type(v) is not int or v < 1 for v in (result.page, result.width_px, result.height_px)):
        raise LayoutConversionError("invalid_page", page=result.page)
    if result.order_base != 0:
        raise LayoutConversionError("invalid_order_base", page=result.page)
    width, height = result.width_px, result.height_px
    regions = []
    for index, region in enumerate(result.regions):
        code = "invalid_class"
        try:
            if type(region.class_id) is not int or not 0 <= region.class_id < len(LABELS):
                raise ValueError()
            if not isinstance(region.label, str) or not region.label:
                raise ValueError()
            code = "invalid_score"
            if not math.isfinite(region.score) or not 0 <= region.score <= 1:
                raise ValueError()
            code = "invalid_order"
            if region.order is not None and (type(region.order) is not int or not 0 <= region.order < 300):
                raise ValueError()
            code = "invalid_box"
            if len(region.box_px) != 4 or not all(math.isfinite(v) for v in region.box_px):
                raise ValueError()
            x0, y0, x1, y1 = region.box_px
            clipped = (max(0, x0), max(0, y0), min(width, x1), min(height, y1))
            if not (clipped[0] < clipped[2] and clipped[1] < clipped[3]):
                raise ValueError()
            code = "invalid_polygon"
            raw_points, polygon, polygon_clipped, contour_status = _normalized_contour(region.polygon_px, width, height)
            if region.contour_source == "aabb_fallback":
                polygon, polygon_clipped, contour_status = (), False, "unusable"
            canonical = LABELS[region.class_id]
            regions.append(NormalizedLayoutRegion(
                index=index, class_id=region.class_id, raw_label=region.label, canonical_label=canonical,
                role_hint=ROLE_HINTS[canonical], score=region.score, box_px=region.box_px,
                polygon_px=raw_points, bbox=BBox(page=result.page, xyxy=tuple(
                    v / dimension for v, dimension in zip(clipped, (width, height, width, height)))),
                polygon=polygon, order=region.order, box_clipped=tuple(region.box_px) != clipped,
                polygon_clipped=polygon_clipped, contour_status=contour_status,
                contour_source=region.contour_source,
            ))
        except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
            raise LayoutConversionError(code, page=result.page, region_index=index) from exc
    return NormalizedLayoutPage(
        page=result.page, width_px=width, height_px=height, regions=tuple(regions),
        model_id=result.model_id, revision=result.revision, engine=result.engine,
        device=result.device, fallback_reason=result.fallback_reason, order_base=result.order_base,
        execution_failures=result.execution_failures,
    )


def _valid_box(box, page):
    return (box is not None and box.page == page and len(box.xyxy) == 4
            and all(math.isfinite(v) and 0 <= v <= 1 for v in box.xyxy)
            and box.xyxy[0] < box.xyxy[2] and box.xyxy[1] < box.xyxy[3])


def _evidence(block_index, box, region):
    a, b = box.xyxy, region.bbox.xyxy
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    if region.contour_status == "valid":
        points = list(region.polygon)
        area_b = _polygon_area(points)
        intersection = _polygon_area(_clip_to_box(points, a))
    else:
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    if area_b <= 0 or intersection > min(area_a, area_b) + 1e-12 * max(area_a, area_b):
        raise ReconciliationInvariantError("Invalid overlap area")
    intersection = min(intersection, area_a, area_b)
    if intersection == 0:
        return None
    return MatchEvidence(
        block_index=block_index, region_index=region.index, score=region.score,
        iou=intersection / (area_a + area_b - intersection),
        sol_coverage=intersection / area_a, region_coverage=intersection / area_b,
        center_distance=math.hypot(a[0] + a[2] - b[0] - b[2], a[1] + a[3] - b[1] - b[3]) / (2 * math.sqrt(2)),
        geometry="polygon" if region.contour_status == "valid" else "aabb",
        geometry_fallback_reason=None if region.contour_status == "valid" else region.contour_status,
    )


def _rank(candidate):
    return (-candidate.iou, candidate.center_distance, candidate.block_index, candidate.region_index)


def _complex_components(candidates, policy):
    neighbors = defaultdict(set)
    for candidate in candidates:
        if max(candidate.sol_coverage, candidate.region_coverage) >= policy.significant_coverage:
            b, r = ("block", candidate.block_index), ("region", candidate.region_index)
            neighbors[b].add(r)
            neighbors[r].add(b)
    reasons, visited = {}, set()
    for node in sorted(neighbors):
        if node in visited:
            continue
        pending, component = [node], set()
        while pending:
            current = pending.pop()
            if current not in component:
                component.add(current)
                pending.extend(neighbors[current] - component)
        visited.update(component)
        blocks = sum(kind == "block" for kind, _ in component)
        regions = len(component) - blocks
        if blocks > 1 or regions > 1:
            reason = "many_to_many" if blocks > 1 and regions > 1 else "split" if regions > 1 else "merge"
            reasons.update(dict.fromkeys(component, reason))
    return reasons


def check_reconciliation(original, output, artifact):
    """Verify ownership and permutation at both direct and parser boundaries."""
    from src.layout import LayoutPageArtifact
    try:
        checked = LayoutPageArtifact.model_validate(artifact.model_dump())
        checked.check_parsed_page(output)
        if checked.reconciliation is None or len(original.blocks) != len(output.blocks):
            raise ValueError("Missing reconciliation or changed block count")
        for decision in checked.reconciliation.decisions:
            before = original.blocks[decision.original_index]
            after = output.blocks[decision.output_index]
            if before.model_dump(exclude={"bbox"}) != after.model_dump(exclude={"bbox"}):
                raise ValueError("Transcription changed")
            if decision.region_index is None and before.bbox != after.bbox:
                # JSON comparison also preserves the existing invalid-NaN box contract.
                if (before.bbox is None or after.bbox is None
                        or before.bbox.model_dump_json() != after.bbox.model_dump_json()):
                    raise ValueError("Unmatched geometry changed")
        slots = [d.original_index for d in checked.reconciliation.decisions
                 if d.region_index is not None and checked.layout.regions[d.region_index].order is not None]
        ranked = sorted(slots, key=lambda i: (
            checked.layout.regions[checked.reconciliation.decisions[i].region_index].order,
            i, checked.reconciliation.decisions[i].region_index))
        expected = dict(enumerate(range(len(original.blocks))))
        expected.update({original_index: slot for slot, original_index in zip(slots, ranked)})
        if any(d.output_index != expected[d.original_index] for d in checked.reconciliation.decisions):
            raise ValueError("Invalid interleaving")
    except (ValueError, TypeError, IndexError, KeyError) as exc:
        raise ReconciliationInvariantError("Reconciliation invariant violated") from exc


def reconcile_page(page: ParsePage, layout: NormalizedLayoutPage,
                   policy: ReconcilePolicy | None = None) -> ReconciliationResult:
    """Assign qualified pairs once; V3 owns geometry, Sol owns all content."""
    from src.layout import LayoutPageArtifact, ReconciliationDetails
    policy = policy if policy is not None else ReconcilePolicy()
    policy.check_active()
    if (page.page, page.width_px, page.height_px) != (layout.page, layout.width_px, layout.height_px):
        raise ReconciliationInvariantError("Page dimensions disagree")
    try:
        layout = NormalizedLayoutPage.model_validate(layout.model_dump())
    except ValueError as exc:
        raise ReconciliationInvariantError("Invalid normalized layout") from exc
    candidates, by_block = [], defaultdict(list)
    # O(blocks * regions * contour vertices), without an optional geometry dependency.
    for i, block in enumerate(page.blocks):
        if not _valid_box(block.bbox, page.page):
            continue
        for region in layout.regions:
            candidate = _evidence(i, block.bbox, region)
            if candidate is not None:
                candidates.append(candidate)
    topology = _complex_components(candidates, policy)
    evidence = []
    for candidate in candidates:
        i, j = candidate.block_index, candidate.region_index
        region = layout.regions[j]
        reasons, flags = [], []
        if page.blocks[i].type not in CLASS_COMPATIBILITY[region.canonical_label]:
            reasons.append("role_disagreement")
        if candidate.score < policy.min_score:
            reasons.append("low_score")
        if (max(candidate.sol_coverage, candidate.region_coverage) < policy.min_coverage
                or min(candidate.sol_coverage, candidate.region_coverage) < policy.min_partial_coverage):
            reasons.append("weak_overlap")
        for node in (("block", i), ("region", j)):
            if node in topology and topology[node] not in flags:
                flags.append(topology[node])
        if region.order is None:
            flags.append("missing_order")
        if region.raw_label != region.canonical_label:
            flags.append("label_alias")
        if candidate.geometry == "aabb":
            flags.append("contour_fallback")
        evidence.append(candidate.model_copy(update={"reasons": tuple(reasons), "review_flags": tuple(flags)}))

    accepted, used_regions = {}, set()
    for candidate in sorted((c for c in evidence if not c.reasons), key=_rank):
        i, j = candidate.block_index, candidate.region_index
        if i not in accepted and j not in used_regions:
            accepted[i] = j
            used_regions.add(j)
    evidence = [
        c.model_copy(update={"reasons": ("assignment_conflict",)})
        if not c.reasons and accepted.get(c.block_index) != c.region_index else c
        for c in evidence
    ]
    for candidate in evidence:
        by_block[candidate.block_index].append(candidate)
    for group in by_block.values():
        group.sort(key=_rank)
    output = page.model_copy(deep=True)
    for i, j in accepted.items():
        output.blocks[i].bbox = layout.regions[j].bbox.model_copy(deep=True)
    slots = sorted(i for i, j in accepted.items() if layout.regions[j].order is not None)
    ordered = sorted(slots, key=lambda i: (layout.regions[accepted[i]].order, i, accepted[i]))
    blocks = list(output.blocks)
    output_indices = dict(enumerate(range(len(blocks))))
    for slot, original in zip(slots, ordered):
        output.blocks[slot] = blocks[original]
        output_indices[original] = slot
    lookup = {(c.block_index, c.region_index): c for c in evidence}
    decisions = []
    for i, block in enumerate(page.blocks):
        j = accepted.get(i)
        flags = ()
        if j is not None:
            reasons, flags = (), lookup[i, j].review_flags
        elif block.bbox is None:
            reasons = ("missing_box",)
        elif not _valid_box(block.bbox, page.page):
            reasons = ("invalid_box",)
        elif not by_block[i]:
            reasons = ("no_overlap",)
        else:
            best = next((c for c in by_block[i] if c.reasons == ("assignment_conflict",)), by_block[i][0])
            reasons, flags = best.reasons, best.review_flags
        decisions.append(BlockDecision(original_index=i, output_index=output_indices[i],
                                       region_index=j, reasons=tuple(reasons), review_flags=flags))
    details = ReconciliationDetails(
        policy_version="v3-authoritative-v1", policy=policy, candidates=tuple(evidence), decisions=tuple(decisions),
        unmatched_region_indices=tuple(r.index for r in layout.regions if r.index not in used_regions),
    )
    artifact = LayoutPageArtifact(layout=layout.model_copy(deep=True), reconciliation=details)
    check_reconciliation(page, output, artifact)
    return ReconciliationResult(page=output, metadata=ReconciliationMetadata(
        layout=artifact.layout, **details.model_dump(),
    ))
