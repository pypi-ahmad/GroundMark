# PP-DocLayoutV3 ONNX: Features and Full Decoding

Research date: 2026-09-27.

Weight repository: [`PaddlePaddle/PP-DocLayoutV3_onnx`](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx).

GroundMark constraint: keep this ONNX weight repository and use its full decode path. Do not switch the weight repository to `PaddlePaddle/PP-DocLayoutV3`.

## Findings and verification scope

`PaddlePaddle/PP-DocLayoutV3_onnx` supports 25 layout classes, bounding boxes, instance masks, and learned reading order. Full decoding is possible while keeping the ONNX repository.

This research checked the live repository, inspected the actual ONNX graph, and traced PaddleDetection and PaddleX decoding code. The export already decodes boxes, reading-order ranks, and binary masks. Application code must correctly process all three outputs.

This initial research did not test document inference, accuracy, speed, batch execution, or GroundMark's decoder. The later [completion report](V3-INTEGRATION-COMPLETION.md) records real CPU/CUDA inference and official-routine comparisons. Recommendations below describe the research scope, not evidence that every optional capability is enabled.

## 1. Model features

| Feature | Output or capability |
|---|---|
| Layout classification | Class ID and confidence for each detected region |
| Bounding boxes | Axis-aligned `[xmin, ymin, xmax, ymax]` coordinates |
| Instance segmentation | Separate mask for each detected region; supports irregular boundaries |
| Reading order | Learned ordering of regions, including complex multi-column layouts |
| Distorted-document handling | Designed for skewed pages, curved surfaces, screen photographs, and lighting variation |

The architecture uses RT-DETR with a PPHGNetV2-L backbone, a segmentation head, and integrated reading-order prediction. These tasks share one forward pass. Robustness is a design and training objective, not a guarantee for every document.

Sources: [official model card](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx), [PaddleX documentation](https://paddlepaddle.github.io/PaddleX/latest/en/module_usage/tutorials/ocr_modules/layout_analysis.html).

### Exact class mapping

| IDs | Labels, in ID order |
|---|---|
| 0–4 | `abstract`, `algorithm`, `aside_text`, `chart`, `content` |
| 5–9 | `display_formula`, `doc_title`, `figure_title`, `footer`, `footer_image` |
| 10–14 | `footnote`, `formula_number`, `header`, `header_image`, `image` |
| 15–19 | `inline_formula`, `number`, `paragraph_title`, `reference`, `reference_content` |
| 20–24 | `seal`, `table`, `text`, `vertical_text`, `vision_footnote` |

Use this exact mapping. Another layout model's label order would corrupt classification.

Source: [repository configuration](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx/blob/46bbdf188bb0a772c08aed74882ce7e51a8f1ea6/inference.yml).

## 2. Verified ONNX artifact and tensor contract

The inspected repository revision was:

```text
46bbdf188bb0a772c08aed74882ce7e51a8f1ea6
```

Direct inspection of `inference.onnx` established:

```text
Size:   130,502,049 bytes
Opset:  17
SHA256: 45bf71750b00739a41fc209f132eb104a4d6b5bb29483c9078164d8b87cf28ba
```

Source artifact: [pinned ONNX repository files](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx/tree/46bbdf188bb0a772c08aed74882ce7e51a8f1ea6).

### Inputs and preprocessing

| Name | Type and shape | Meaning |
|---|---|---|
| `image` | float32 `[B,3,800,800]` | RGB image tensor |
| `im_shape` | float32 `[B,2]` | Resized height and width |
| `scale_factor` | float32 `[B,2]` | Height and width resize factors |

For an original image of height `H` and width `W`:

```text
im_shape     = [800, 800]
scale_factor = [800/H, 800/W]
```

Resize directly to 800×800 without preserving aspect ratio. Use cubic interpolation, scale pixels by `1/255`, and convert HWC to CHW. Despite `norm_type: none`, upstream preprocessing still applies pixel scaling; mean is zero and standard deviation is one.

Sources: [configuration](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx/blob/46bbdf188bb0a772c08aed74882ce7e51a8f1ea6/inference.yml), [preprocessing builder](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/object_detection/predictor.py), [resize and batching implementation](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/object_detection/processors.py).

### Outputs

| Name | Type and shape | Meaning |
|---|---|---|
| `fetch_name_0` | float32 `[N,7]` | Class, score, box, reading-order rank |
| `fetch_name_1` | int32 `[B]` | Number of candidate rows per image |
| `fetch_name_2` | int32 `[N,200,200]` | Corresponding binary instance masks |

Each detection row is:

```text
[class_id, score, xmin, ymin, xmax, ymax, order_rank]
```

Boxes are already mapped to original-image pixels when input metadata is correct. Masks remain on the 200×200 grid. They are already binarized, not raw logits.

Upstream configuration selects 300 candidates per image before application confidence filtering. The graph exposes dynamic batch dimensions, but that alone does not establish reliable multi-image execution. Batch inference was not tested in this research.

Sources: direct inspection of the pinned ONNX artifact; [model configuration](https://github.com/PaddlePaddle/PaddleDetection/blob/65e643573a35e068c796527648f7c2166de09cce/configs/layout_analysis/PP-DocLayoutV3.yaml), [decoder source](https://github.com/PaddlePaddle/PaddleDetection/blob/65e643573a35e068c796527648f7c2166de09cce/ppdet/modeling/post_process.py).

## 3. Meaning of full decode

“Full decode” is not a named switch in the repository. For this export, it means preserving and interpreting every exposed output.

1. Preprocess correctly: supply RGB pixels, expected scaling, 800×800 dimensions, and correct resize factors.
2. Read all three outputs: split detections and masks by per-image counts, keeping each mask attached to its detection.
3. Filter consistently: apply the same selection indices to boxes, masks, labels, scores, and order ranks.
4. Restore geometry: decode masks into original-image polygons; retain masks if exact exported segmentation must remain available.
5. Restore reading sequence: sort retained regions by the seventh column and preserve raw rank separately from any renumbered display order.

The upstream batch formatter explicitly keeps detection rows and masks aligned. [Batch-output implementation](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/object_detection/predictor.py).

### Reading-order decoding

Reading order is learned through pairwise precedence scores. Internally, the decoder applies sigmoid, excludes self-relations, sums precedence votes, and converts their ordering into ranks. This happens before export outputs reach application code.

Replacing those ranks with a top-to-bottom coordinate sort discards the model's ordering prediction.

Sources: [technical report, section 2.1.1](https://arxiv.org/html/2601.21957v1#S2.SS1.SSS1), [order decoder](https://github.com/PaddlePaddle/PaddleDetection/blob/65e643573a35e068c796527648f7c2166de09cce/ppdet/modeling/post_process.py).

Raw class logits, pairwise order logits, and soft mask probabilities are not exposed by these three graph outputs. Full decoding cannot recover information the export does not return.

## 4. Polygon decoding and optional post-processing

PaddleX derives polygons by cropping the corresponding mask region, resizing it to the detected box with nearest-neighbor interpolation, extracting the largest external contour, simplifying it, and translating points into original-image coordinates. Empty or unsuitable contours can fall back to rectangles.

That conversion is lossy: holes, smaller disconnected components, and some boundary detail can disappear. Keeping the binary mask alongside the polygon preserves more information.

### Shape modes

| Mode | Result |
|---|---|
| `rect` | Axis-aligned rectangle; bypasses segmentation geometry |
| `quad` | Four-point rotated rectangle derived from the polygon |
| `poly` | Multi-point contour |
| `auto` | Chooses rectangle, quadrilateral, or polygon using geometric heuristics |

For maximum contour detail among these modes, `poly` is relevant. `auto` can intentionally simplify a detected shape. Even `poly` uses contour processing and is not a lossless representation of the original binary mask.

Source: [pinned polygon implementation](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/layout_analysis/processors.py).

### Processing controls

- Global or per-class confidence thresholds; the repository default is `0.5`.
- Optional layout NMS; the inspected implementation uses IoU thresholds `0.6` within a class and `0.98` across classes.
- Box expansion through `layout_unclip_ratio`.
- Containment handling through `union`, `large`, and `small`; `union` leaves this containment filtering inactive.
- Overlap filtering and configurable labels excluded from displayed reading-order numbering.

These are application policies, not additional neural outputs. [Post-processing implementation](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/layout_analysis/processors.py).

### Defaults that can discard information

The inspected PaddleX overlap filter removes `reference` detections, drops very small regions, and can remove overlapping inline formulas. Its order formatter assigns `None` to skipped categories, including tables, images, charts, captions, headers, and footers.

Documentation describes zero-based `order`, while the inspected current code renumbers included regions from 1. Preserve raw model rank separately from display order, and pin the decoder version.

Sources: [documentation](https://paddlepaddle.github.io/PaddleX/latest/en/module_usage/tutorials/ocr_modules/layout_analysis.html), [filtering and order-formatting source](https://github.com/PaddlePaddle/PaddleX/blob/c50f5da858020db473a2285f089bb8c7bbd6afdc/paddlex/inference/models/layout_analysis/processors.py).

## 5. Capability boundaries

PP-DocLayoutV3 locates and classifies regions. It does not itself transcribe text, recognize table cells, produce LaTeX, read seal text, determine heading levels, merge cross-page tables, or generate Markdown.

Those functions belong to recognition models and downstream processing. The technical report explicitly separates layout analysis from element recognition. [Pipeline architecture](https://arxiv.org/html/2601.21957v1#S2.SS1).

## 6. Performance and licensing

Official documentation reports 23.77 ms on an A100, excluding preprocessing and post-processing. This is not a measured ONNX latency on the user's Windows machine.

The model repository declares Apache-2.0 licensing.

Sources: [official timing](https://paddlepaddle.github.io/PaddleX/latest/en/module_usage/tutorials/ocr_modules/layout_analysis.html), [license metadata](https://huggingface.co/PaddlePaddle/PP-DocLayoutV3_onnx).

## 7. Recommendations for GroundMark

Retain the following information through decoding:

```text
class_id + label + confidence
original-image bbox
binary mask + multi-point polygon
raw model order_rank + application display_order
model revision + decoder version + filtering settings
```

Keep `PaddlePaddle/PP-DocLayoutV3_onnx` as the weight source. `Global.model_name: PP-DocLayoutV3` inside its configuration is the architecture identifier; it does not require changing repositories.

Do not describe a decoder that discards masks or learned order as a full decoder. Distinguish preserved model outputs from optional filtering and display policies.

These were research recommendations, not a description of the current runtime. The subsequent [integration report](V3-INTEGRATION-COMPLETION.md) verifies preprocessing, the three ONNX outputs, polygon extraction, CPU/CUDA execution, and saved-response replay. GroundMark retains the upstream polygon and contour provenance in layout metadata; it does not persist the original binary masks, separate display-order values, or an independent decoder-version field. The graph does not expose raw logits or soft mask probabilities.
