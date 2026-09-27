# Copyright (c) 2024 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""PaddleX poly-mode decode, adapted from commit c50f5da858020db473a2285f089bb8c7bbd6afdc.
Source: paddlex/inference/models/layout_analysis/processors.py.
Dependency decorators, unused helpers, and unused layout modes are removed.
Imported lazily by the ONNX backend.
"""

import cv2
import numpy as np

def is_convex(p_prev, p_curr, p_next):
    """
    Calculate if the polygon is convex.
    """
    v1 = p_curr - p_prev
    v2 = p_next - p_curr
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    return cross < 0


def angle_between_vectors(v1, v2):
    """
    Calculate the angle between two vectors.
    """

    unit_v1 = v1 / np.linalg.norm(v1)
    unit_v2 = v2 / np.linalg.norm(v2)
    dot_prod = np.clip(np.dot(unit_v1, unit_v2), -1.0, 1.0)
    angle_rad = np.arccos(dot_prod)
    return np.degrees(angle_rad)


def extract_custom_vertices(
    polygon, max_allowed_dist, sharp_angle_thresh=45, max_dist_ratio=0.3
):
    poly = np.array(polygon)
    n = len(poly)
    max_allowed_dist *= max_dist_ratio

    point_info = []
    for i in range(n):
        p_prev, p_curr, p_next = poly[(i - 1) % n], poly[i], poly[(i + 1) % n]
        v1, v2 = p_prev - p_curr, p_next - p_curr
        is_convex_point = is_convex(p_prev, p_curr, p_next)
        angle = angle_between_vectors(v1, v2)
        point_info.append(
            {
                "index": i,
                "is_convex": is_convex_point,
                "angle": angle,
                "v1": v1,
                "v2": v2,
            }
        )

    concave_indices = [i for i, info in enumerate(point_info) if not info["is_convex"]]
    preserve_concave = set()

    if concave_indices:
        groups = []
        current_group = [concave_indices[0]]

        for i in range(1, len(concave_indices)):
            if concave_indices[i] - concave_indices[i - 1] == 1 or (
                concave_indices[i - 1] == n - 1 and concave_indices[i] == 0
            ):
                current_group.append(concave_indices[i])
            else:
                if len(current_group) >= 2:
                    groups.extend(current_group)
                current_group = [concave_indices[i]]

        if len(current_group) >= 2:
            groups.extend(current_group)

        if (
            len(concave_indices) >= 2
            and concave_indices[0] == 0
            and concave_indices[-1] == n - 1
        ):
            if 0 in groups and n - 1 in groups:
                preserve_concave.update(groups)
        else:
            preserve_concave.update(groups)

    kept_points = [
        i
        for i, info in enumerate(point_info)
        if info["is_convex"] or (i in preserve_concave and info["angle"] >= 120)
    ]

    final_points = []
    for idx in range(len(kept_points)):
        current_idx = kept_points[idx]
        next_idx = kept_points[(idx + 1) % len(kept_points)]
        final_points.append(current_idx)

        dist = np.linalg.norm(poly[current_idx] - poly[next_idx])
        if dist > max_allowed_dist:
            intermediate = (
                list(range(current_idx + 1, next_idx))
                if next_idx > current_idx
                else list(range(current_idx + 1, n)) + list(range(0, next_idx))
            )

            if intermediate:
                num_needed = int(np.ceil(dist / max_allowed_dist)) - 1
                if len(intermediate) <= num_needed:
                    final_points.extend(intermediate)
                else:
                    step = len(intermediate) / num_needed
                    final_points.extend(
                        [intermediate[int(i * step)] for i in range(num_needed)]
                    )

    final_points = sorted(set(final_points))
    res = []

    for i in final_points:
        info = point_info[i]
        p_curr = poly[i]

        if info["is_convex"] and abs(info["angle"] - sharp_angle_thresh) < 1:
            v1_norm = info["v1"] / np.linalg.norm(info["v1"])
            v2_norm = info["v2"] / np.linalg.norm(info["v2"])
            dir_vec = v1_norm + v2_norm
            dir_vec /= np.linalg.norm(dir_vec)
            d = (np.linalg.norm(info["v1"]) + np.linalg.norm(info["v2"])) / 2
            res.append(tuple(p_curr + dir_vec * d))
        else:
            res.append(tuple(p_curr))

    return res


def mask2polygon(mask, max_allowed_dist, epsilon_ratio=0.004, extract_custom=True):
    """
    Postprocess mask by removing small noise.
    Args:
        mask (ndarray): The input mask of shape [H, W].
        epsilon_ratio (float): The ratio of epsilon.
    Returns:
        ndarray: The output mask after postprocessing.
    """
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not cnts:
        return None

    cnt = max(cnts, key=cv2.contourArea)
    epsilon = epsilon_ratio * cv2.arcLength(cnt, True)
    approx_cnt = cv2.approxPolyDP(cnt, epsilon, True)
    polygon_points = approx_cnt.squeeze()
    polygon_points = np.atleast_2d(polygon_points)
    if extract_custom:
        polygon_points = extract_custom_vertices(polygon_points, max_allowed_dist)

    return polygon_points


def extract_polygon_points_by_masks(boxes, masks, scale_ratio, layout_shape_mode, *, sources=None):
    """
    修改后的提取函数：auto 模式下信任几何决策
    """
    scale_w, scale_h = scale_ratio[0] / 4, scale_ratio[1] / 4
    h_m, w_m = masks.shape[1:]
    polygon_points = []

    max_box_w = max(boxes[:, 4] - boxes[:, 3])

    for i in range(len(boxes)):
        if sources is not None:
            sources.append("aabb_fallback")
        x_min, y_min, x_max, y_max = boxes[i, 2:6].astype(np.int32)
        box_w, box_h = x_max - x_min, y_max - y_min
        rect = _rect_from_box(boxes[i, 2:6])

        if box_w <= 0 or box_h <= 0:
            polygon_points.append(rect)
            continue

        # crop mask
        x_s = np.clip(
            [int(round(x_min * scale_w)), int(round(x_max * scale_w))], 0, w_m
        )
        y_s = np.clip(
            [int(round(y_min * scale_h)), int(round(y_max * scale_h))], 0, h_m
        )

        cropped = masks[i, y_s[0] : y_s[1], x_s[0] : x_s[1]]
        if cropped.size == 0 or np.sum(cropped) == 0:
            polygon_points.append(rect)
            continue

        # resize mask to match box size
        resized_mask = cv2.resize(
            cropped.astype(np.uint8), (box_w, box_h), interpolation=cv2.INTER_NEAREST
        )

        if box_w > max_box_w * 0.6:
            max_allowed_dist = box_w
        else:
            max_allowed_dist = max_box_w

        polygon = mask2polygon(resized_mask, max_allowed_dist)
        if polygon is not None and len(polygon) > 0:
            polygon = polygon + np.array([x_min, y_min])
        if sources is not None and polygon is not None and len(polygon) >= 4:
            sources[-1] = "mask"
        polygon_points.append(
            _normalize_layout_polygon(
                box=boxes[i, 2:6],
                polygon=polygon,
                layout_shape_mode=layout_shape_mode,
                previous_polygon=(
                    polygon_points[-1] if len(polygon_points) > 0 else None
                ),
            )
        )

    return polygon_points


def _rect_from_box(box):
    x_min, y_min, x_max, y_max = np.asarray(box).astype(np.int32)
    return np.array(
        [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]],
        dtype=np.float32,
    )


def _normalize_layout_polygon(box, polygon, layout_shape_mode, previous_polygon=None):
    """Fixed poly mode; retain upstream rectangle fallback for tiny contours."""
    if polygon is None:
        return _rect_from_box(box)
    polygon = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
    return polygon if len(polygon) >= 4 else _rect_from_box(box)
