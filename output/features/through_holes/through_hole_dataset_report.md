# Through-hole dataset report

Dataset folder: `/Users/hassenhicheri/Desktop/CAD/output/features/through_holes`

## Category counts
- **centered_single**: 30
- **off_center_single**: 16
- **thin_plate**: 12
- **two_holes**: 10
- **four_holes**: 7

## Totals
- Unique geometries: **75**
- Prompt/target pairs: **375**
- Validation pass: **75**
- Validation fail: **0**

## Example: centered_single
- shape_id: `through_hole_01_l60_w40_h20_d10mm`

### Prompts (all variants)
1. Create a rectangular prism 60 mm long, 40 mm wide, and 20 mm high, with a centered through-hole of 10 mm diameter going through the entire height of the prism.
2. Generate a 60 × 40 × 20 mm block with a centered 10 mm diameter through-hole.
3. Make a 60 by 40 by 20 millimeter rectangular prism with a 10 mm hole through the full height.
4. Build a rectangular block measuring 60 × 40 × 20 mm with a centered circular through-hole of diameter 10 mm.
5. I need a 60 mm × 40 mm × 20 mm prism with a 10 mm diameter hole through all.

### Canonical CAD JSON (operations)
```json
[
  {
    "id": "op_001",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Line",
        "start": [
          0.0,
          0.0
        ],
        "end": [
          60.0,
          0.0
        ]
      },
      {
        "id": "e_002",
        "type": "Line",
        "start": [
          60.0,
          0.0
        ],
        "end": [
          60.0,
          40.0
        ]
      },
      {
        "id": "e_003",
        "type": "Line",
        "start": [
          60.0,
          40.0
        ],
        "end": [
          0.0,
          40.0
        ]
      },
      {
        "id": "e_004",
        "type": "Line",
        "start": [
          0.0,
          40.0
        ],
        "end": [
          0.0,
          0.0
        ]
      }
    ],
    "constraints": [],
    "plane": "XY"
  },
  {
    "id": "op_002",
    "type": "Pad",
    "profile": "op_001",
    "length": 20.0
  },
  {
    "id": "op_003",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Circle",
        "center": [
          30.0,
          20.0
        ],
        "radius": 5.0
      }
    ],
    "constraints": [],
    "support": {
      "type": "face",
      "reference": "op_002",
      "selector": "Face6"
    }
  },
  {
    "id": "op_004",
    "type": "Hole",
    "profile": "op_003",
    "diameter": 10.0,
    "depth": "through_all"
  }
]
```

## Example: off_center_single
- shape_id: `through_hole_31_l80_w50_h20_d10mm_x18_y22`

### Prompts (all variants)
1. Create a 80 × 50 × 20 mm rectangular block with a 10 mm diameter through-hole located 18 mm from the left edge and 22 mm from the bottom edge.
2. Generate a 80 by 50 by 20 millimeter prism with a through-hole of 10 mm passing fully through, with the hole center at (18, 22).
3. Make a 80 mm long, 50 mm wide, and 20 mm high block with a 10 mm diameter hole through all. Position it 18 mm from the left edge and 22 mm from the bottom edge.
4. Build a rectangular solid measuring 80 × 50 × 20 mm with a 10 mm through hole at hole center (18, 22).
5. I need a 80 × 50 × 20 mm prism featuring a 10 mm hole through all. The hole center is at (18, 22).

### Canonical CAD JSON (operations)
```json
[
  {
    "id": "op_001",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Line",
        "start": [
          0.0,
          0.0
        ],
        "end": [
          80.0,
          0.0
        ]
      },
      {
        "id": "e_002",
        "type": "Line",
        "start": [
          80.0,
          0.0
        ],
        "end": [
          80.0,
          50.0
        ]
      },
      {
        "id": "e_003",
        "type": "Line",
        "start": [
          80.0,
          50.0
        ],
        "end": [
          0.0,
          50.0
        ]
      },
      {
        "id": "e_004",
        "type": "Line",
        "start": [
          0.0,
          50.0
        ],
        "end": [
          0.0,
          0.0
        ]
      }
    ],
    "constraints": [],
    "plane": "XY"
  },
  {
    "id": "op_002",
    "type": "Pad",
    "profile": "op_001",
    "length": 20.0
  },
  {
    "id": "op_003",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Circle",
        "center": [
          18.0,
          22.0
        ],
        "radius": 5.0
      }
    ],
    "constraints": [],
    "support": {
      "type": "face",
      "reference": "op_002",
      "selector": "Face6"
    }
  },
  {
    "id": "op_004",
    "type": "Hole",
    "profile": "op_003",
    "diameter": 10.0,
    "depth": "through_all"
  }
]
```

## Example: two_holes
- shape_id: `through_hole_59_l100_w50_h10_d8mm_n2_x25_y25_x75_y25`

### Prompts (all variants)
1. Create a 100 × 50 × 10 mm plate with two 8 mm diameter through-holes at positions (25, 25) and (75, 25).
2. Generate a 100 by 50 by 10 millimeter block with two through-holes ((25, 25)) and ((75, 25)), each passing through the full height.
3. Make a 100 mm long, 50 mm wide, and 10 mm high rectangular prism with two 8 mm holes through all, hole centers at (25, 25) and (75, 25).
4. Build a rectangular solid measuring 100 × 50 × 10 mm with two 8 mm through-holes placed at (25, 25) and (75, 25).
5. I need a 100 × 50 × 10 mm prism containing two 8 mm through holes. Place their centers at (25, 25) and (75, 25).

### Canonical CAD JSON (operations)
```json
[
  {
    "id": "op_001",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Line",
        "start": [
          0.0,
          0.0
        ],
        "end": [
          100.0,
          0.0
        ]
      },
      {
        "id": "e_002",
        "type": "Line",
        "start": [
          100.0,
          0.0
        ],
        "end": [
          100.0,
          50.0
        ]
      },
      {
        "id": "e_003",
        "type": "Line",
        "start": [
          100.0,
          50.0
        ],
        "end": [
          0.0,
          50.0
        ]
      },
      {
        "id": "e_004",
        "type": "Line",
        "start": [
          0.0,
          50.0
        ],
        "end": [
          0.0,
          0.0
        ]
      }
    ],
    "constraints": [],
    "plane": "XY"
  },
  {
    "id": "op_002",
    "type": "Pad",
    "profile": "op_001",
    "length": 10.0
  },
  {
    "id": "op_003",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Circle",
        "center": [
          25.0,
          25.0
        ],
        "radius": 4.0
      },
      {
        "id": "e_002",
        "type": "Circle",
        "center": [
          75.0,
          25.0
        ],
        "radius": 4.0
      }
    ],
    "constraints": [],
    "support": {
      "type": "face",
      "reference": "op_002",
      "selector": "Face6"
    }
  },
  {
    "id": "op_004",
    "type": "Hole",
    "profile": "op_003",
    "diameter": 8.0,
    "depth": "through_all"
  }
]
```

## Example: four_holes
- shape_id: `through_hole_69_l120_w80_h5_d6mm_n4_x6_y6_x6_y74_x114_y6_x114_y74`

### Prompts (all variants)
1. Create a 120 × 80 × 5 mm plate with four 6 mm diameter through-holes at positions (6, 6), (6, 74), (114, 6), and (114, 74).
2. Generate a 120 by 80 by 5 millimeter block with four through holes ((6, 6)), ((6, 74)), ((114, 6)), and ((114, 74)), each going through the full thickness.
3. Make a 120 mm long, 80 mm wide, and 5 mm high rectangular prism with four 6 mm holes through all, hole centers at (6, 6), (6, 74), (114, 6), (114, 74).
4. Build a rectangular solid measuring 120 × 80 × 5 mm with four 6 mm through-holes at (6, 6), (6, 74), (114, 6), and (114, 74).
5. I need a 120 × 80 × 5 mm prism featuring four 6 mm through holes. Place their centers at (6, 6), (6, 74), (114, 6), and (114, 74).

### Canonical CAD JSON (operations)
```json
[
  {
    "id": "op_001",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Line",
        "start": [
          0.0,
          0.0
        ],
        "end": [
          120.0,
          0.0
        ]
      },
      {
        "id": "e_002",
        "type": "Line",
        "start": [
          120.0,
          0.0
        ],
        "end": [
          120.0,
          80.0
        ]
      },
      {
        "id": "e_003",
        "type": "Line",
        "start": [
          120.0,
          80.0
        ],
        "end": [
          0.0,
          80.0
        ]
      },
      {
        "id": "e_004",
        "type": "Line",
        "start": [
          0.0,
          80.0
        ],
        "end": [
          0.0,
          0.0
        ]
      }
    ],
    "constraints": [],
    "plane": "XY"
  },
  {
    "id": "op_002",
    "type": "Pad",
    "profile": "op_001",
    "length": 5.0
  },
  {
    "id": "op_003",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Circle",
        "center": [
          6.0,
          6.0
        ],
        "radius": 3.0
      },
      {
        "id": "e_002",
        "type": "Circle",
        "center": [
          114.0,
          6.0
        ],
        "radius": 3.0
      },
      {
        "id": "e_003",
        "type": "Circle",
        "center": [
          6.0,
          74.0
        ],
        "radius": 3.0
      },
      {
        "id": "e_004",
        "type": "Circle",
        "center": [
          114.0,
          74.0
        ],
        "radius": 3.0
      }
    ],
    "constraints": [],
    "support": {
      "type": "face",
      "reference": "op_002",
      "selector": "Face6"
    }
  },
  {
    "id": "op_004",
    "type": "Hole",
    "profile": "op_003",
    "diameter": 6.0,
    "depth": "through_all"
  }
]
```

