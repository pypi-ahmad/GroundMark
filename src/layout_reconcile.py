"""Offline V3 geometry conversion and conservative, non-transcribing matching.

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
        "review_blocks": sum(bool(d.reasons) for d in details.decisions) if details else None,
    }


GIVEN_LAYOUT_MAX_BYTES = 64 * 1024
GIVEN_LAYOUT_MAX_REGIONS = 300


def given_layout_json(layout: NormalizedLayoutPage) -> str:
    """Bounded prompt projection; full geometry stays in the artifact."""
    def dump(value):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=True, allow_nan=False)

    if len(layout.regions) > GIVEN_LAYOUT_MAX_REGIONS:
        raise LayoutConversionError("layout_prompt_too_large", page=layout.page)
    regions = sorted(layout.regions, key=lambda r: (r.order is None, r.order or 0, r.index))
    items = []
    for region in regions:
        box = [fn(v * 1_000_000) / 1_000_000 for fn, v in zip(
            (math.floor, math.floor, math.ceil, math.ceil), region.bbox.xyxy)]
        items.append(dict(id=f"r{region.index:03d}", class_id=region.class_id,
                          label=LABELS[region.class_id], bbox=box, score=round(region.score, 4), order=region.order))
    payload = dict(page=layout.page, coordinates="normalized_xyxy", regions=items)
    text = dump(payload)
    if len(text.encode("utf-8")) > GIVEN_LAYOUT_MAX_BYTES:
        raise LayoutConversionError("layout_prompt_too_large", page=layout.page)
    for item, region in zip(items, regions):
        if len(region.polygon) > 8:
            continue
        polygon = [(round(x, 6), round(y, 6)) for x, y in region.polygon]
        xs, ys = {p[0] for p in polygon}, {p[1] for p in polygon}
        if len(polygon) == 4 and len(xs) == len(ys) == 2:
            continue  # A rectangle adds no useful contour information.
        try:
            _validate_polygon(polygon)
        except ValueError:
            continue
        item["polygon_points"] = polygon
        proposed = dump(payload)
        if len(proposed.encode("utf-8")) <= GIVEN_LAYOUT_MAX_BYTES:
            text = proposed
        else:
            del item["polygon_points"]
    return text


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


def _clip_polygon(points, width, height):
    # Sutherland-Hodgman clipping, not independent vertex clamping. A contour
    # requiring multiple disconnected rings is rejected by final validation.
    for axis, bound, lower in ((0, 0, True), (0, width, False), (1, 0, True), (1, height, False)):
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
    _validate_polygon(points)
    return points


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
            if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in region.polygon_px):
                raise ValueError()
            raw_points = tuple(tuple(p) for p in region.polygon_px)
            points = _deduplicate(raw_points)
            _validate_polygon(points)
            clipped_points = _clip_polygon(points, width, height)
            polygon = tuple((x / width, y / height) for x, y in clipped_points)
            _validate_polygon(list(polygon))
            canonical = LABELS[region.class_id]
            regions.append(NormalizedLayoutRegion(
                index=index, class_id=region.class_id, raw_label=region.label, canonical_label=canonical,
                role_hint=ROLE_HINTS[canonical], score=region.score, box_px=region.box_px,
                polygon_px=raw_points, bbox=BBox(page=result.page, xyxy=tuple(
                    v / dimension for v, dimension in zip(clipped, (width, height, width, height)))),
                polygon=polygon, order=region.order, box_clipped=tuple(region.box_px) != clipped,
                polygon_clipped=points != clipped_points,
            ))
        except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
            raise LayoutConversionError(code, page=result.page, region_index=index) from exc
    return NormalizedLayoutPage(
        page=result.page, width_px=width, height_px=height, regions=tuple(regions),
        model_id=result.model_id, revision=result.revision, engine=result.engine,
        device=result.device, fallback_reason=result.fallback_reason, order_base=result.order_base,
    )


def _valid_box(box, page):
    return (box is not None and box.page == page and len(box.xyxy) == 4
            and all(math.isfinite(v) and 0 <= v <= 1 for v in box.xyxy)
            and box.xyxy[0] < box.xyxy[2] and box.xyxy[1] < box.xyxy[3])


def _evidence(block_index, box, region):
    a, b = box.xyxy, region.bbox.xyxy
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    if intersection == 0:
        return None
    area_a, area_b = (a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])
    return MatchEvidence(
        block_index=block_index, region_index=region.index, score=region.score,
        iou=intersection / (area_a + area_b - intersection),
        sol_coverage=intersection / area_a, region_coverage=intersection / area_b,
        center_distance=math.hypot(a[0] + a[2] - b[0] - b[2], a[1] + a[3] - b[1] - b[3]) / (2 * math.sqrt(2)),
    )


def _rank(candidate):
    return (-candidate.iou, candidate.center_distance, -candidate.score, candidate.block_index, candidate.region_index)


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


def reconcile_page(page: ParsePage, layout: NormalizedLayoutPage,
                   policy: ReconcilePolicy | None = None) -> ReconciliationResult:
    """Copy a page, changing only accepted boxes and matched-block positions."""
    policy = policy if policy is not None else ReconcilePolicy()
    if (page.page, page.width_px, page.height_px) != (layout.page, layout.width_px, layout.height_px):
        raise LayoutConversionError("page_mismatch", page=page.page)
    if any(region.index != i or not _valid_box(region.bbox, page.page) for i, region in enumerate(layout.regions)):
        raise LayoutConversionError("invalid_normalized_region", page=page.page)
    candidates, by_block, by_region = [], defaultdict(list), defaultdict(list)
    # ponytail: O(blocks * regions); introduce a spatial index only after measuring large pages.
    for i, block in enumerate(page.blocks):
        if not _valid_box(block.bbox, page.page):
            continue
        for region in layout.regions:
            candidate = _evidence(i, block.bbox, region)
            if candidate is not None:
                candidates.append(candidate)
                by_block[i].append(candidate)
                by_region[region.index].append(candidate)
    for group in (*by_block.values(), *by_region.values()):
        group.sort(key=_rank)
    complex_reasons = _complex_components(candidates, policy)
    accepted, evidence = {}, []
    for candidate in candidates:
        i, j = candidate.block_index, candidate.region_index
        reasons = []
        region = layout.regions[j]
        if region.role_hint != page.blocks[i].type:
            reasons.append("role_disagreement")
        if region.raw_label != region.canonical_label:
            reasons.append("label_disagreement")
        for node in (("block", i), ("region", j)):
            if node in complex_reasons and complex_reasons[node] not in reasons:
                reasons.append(complex_reasons[node])
        if candidate.score < policy.min_score:
            reasons.append("low_score")
        if min(candidate.sol_coverage, candidate.region_coverage) < policy.min_coverage:
            reasons.append("weak_overlap")
        if candidate.center_distance > policy.max_center_distance:
            reasons.append("distant_centers")
        groups = (by_block[i], by_region[j])
        if any(group[0] is not candidate for group in groups):
            reasons.append("not_mutual_best")
        if any(len(group) > 1 and (group[0].iou - group[1].iou <= 0
                                  or group[0].iou - group[1].iou < policy.min_iou_margin) for group in groups):
            reasons.append("ambiguous")
        if not reasons:
            accepted[i] = j
        evidence.append(candidate.model_copy(update={"reasons": tuple(reasons)}))

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
    candidate_lookup = {(c.block_index, c.region_index): c for c in evidence}
    decisions = []
    for i, block in enumerate(page.blocks):
        j = accepted.get(i)
        if j is not None:
            region = layout.regions[j]
            reasons = []
            if region.order is None:
                reasons.append("missing_order")
        elif block.bbox is None:
            reasons = ["missing_box"]
        elif not _valid_box(block.bbox, page.page):
            reasons = ["invalid_box"]
        elif not by_block[i]:
            reasons = ["no_overlap"]
        else:
            best = by_block[i][0]
            reasons = list(candidate_lookup[(i, best.region_index)].reasons)
        decisions.append(BlockDecision(original_index=i, output_index=output_indices[i],
                                       region_index=j, reasons=tuple(reasons)))
    return ReconciliationResult(page=output, metadata=ReconciliationMetadata(
        policy_version="conservative-v2",
        policy=policy, layout=layout.model_copy(deep=True), candidates=tuple(evidence), decisions=tuple(decisions),
        unmatched_region_indices=tuple(r.index for r in layout.regions if r.index not in accepted.values()),
    ))
