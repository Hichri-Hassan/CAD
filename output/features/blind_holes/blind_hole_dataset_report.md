# blind_hole dataset report

Dataset folder: `/Users/hassenhicheri/Desktop/CAD/output/features/blind_holes`

## Category counts
- **cylinder**: 18
- **plate**: 12
- **rect**: 20
- **triangle**: 18

## Totals
- Unique geometries: **68**
- Prompt/target pairs: **340**
- Validation pass: **143**
- Validation fail: **0**

## Example: cylinder
- shape_id: `blind_hole_51_cyl_r20_h50_d10_dp20mm`

### Prompts (all variants)
1. Create a cylinder 40 mm in diameter and 50 mm high with a centered 10 mm diameter blind hole 20 mm deep.
2. Make a cylindrical solid (radius 20 mm, height 50 mm) with a Ø10 mm blind hole drilled 20 mm from the top face, in the center.
3. Generate a cylinder with diameter 40 mm and height 50 mm containing a 10 mm blind hole that stops after 20 mm, in the center.
4. I need a cylinder 40 mm in diameter, 50 mm tall, with a centered 10 mm blind hole 20 mm deep from the top.
5. Build a 40 mm diameter, 50 mm high cylinder with a 10 mm blind hole drilled to a depth of 20 mm, in the center.

### Canonical CAD JSON (operations)
```json
[
  {
    "id": "op_001",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Circle",
        "center": [
          0.0,
          0.0
        ],
        "radius": 20.0
      }
    ],
    "constraints": [],
    "plane": "XY"
  },
  {
    "id": "op_002",
    "type": "Pad",
    "profile": "op_001",
    "length": 50.0
  },
  {
    "id": "op_003",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Circle",
        "center": [
          0.0,
          0.0
        ],
        "radius": 5.0
      }
    ],
    "constraints": [],
    "support": {
      "type": "face",
      "reference": "op_002",
      "selector": "Face3"
    }
  },
  {
    "id": "op_004",
    "type": "Hole",
    "profile": "op_003",
    "diameter": 10.0,
    "depth": 20.0
  }
]
```

## Example: plate
- shape_id: `blind_hole_21_plate_l100_w70_h12_d8_dp7mm`

### Prompts (all variants)
1. Create a 100 × 70 × 12 mm plate with a centered 8 mm diameter blind hole 7 mm deep.
2. Make a 100 by 70 by 12 millimeter rectangular prism with a Ø8 mm blind hole drilled 7 mm into the top face, in the center.
3. Generate a 100 × 70 × 12 mm plate containing a 8 mm diameter hole that stops after 7 mm, in the center.
4. I need a 100 mm × 70 mm × 12 mm plate with a centered 8 mm blind hole 7 mm deep from the top face.
5. Build a rectangular solid measuring 100 × 70 × 12 mm with a 8 mm blind hole drilled to a depth of 7 mm, in the center.

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
          70.0
        ]
      },
      {
        "id": "e_003",
        "type": "Line",
        "start": [
          100.0,
          70.0
        ],
        "end": [
          0.0,
          70.0
        ]
      },
      {
        "id": "e_004",
        "type": "Line",
        "start": [
          0.0,
          70.0
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
    "length": 12.0
  },
  {
    "id": "op_003",
    "type": "Sketch",
    "entities": [
      {
        "id": "e_001",
        "type": "Circle",
        "center": [
          50.0,
          35.0
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
    "depth": 7.0
  }
]
```

## Example: rect
- shape_id: `blind_hole_01_rect_l60_w40_h20_d10_dp8mm`

### Prompts (all variants)
1. Create a 60 × 40 × 20 mm block with a centered 10 mm diameter blind hole 8 mm deep.
2. Make a 60 by 40 by 20 millimeter rectangular prism with a Ø10 mm blind hole drilled 8 mm into the top face, in the center.
3. Generate a 60 × 40 × 20 mm block containing a 10 mm diameter hole that stops after 8 mm, in the center.
4. I need a 60 mm × 40 mm × 20 mm block with a centered 10 mm blind hole 8 mm deep from the top face.
5. Build a rectangular solid measuring 60 × 40 × 20 mm with a 10 mm blind hole drilled to a depth of 8 mm, in the center.

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
    "depth": 8.0
  }
]
```

## Example: triangle
- shape_id: `blind_hole_33_tri_b60_th40_ph30_d8_dp10mm`

### Prompts (all variants)
1. Create a triangular prism with a 60 mm base, 40 mm triangle height, and 30 mm extrusion length, with a centered 8 mm diameter blind hole 10 mm deep.
2. Make a triangular prism (base 60 mm, triangle height 40 mm, length 30 mm) with a Ø8 mm blind hole drilled 10 mm into the top face, in the center.
3. Generate a 60 × 40 × 30 mm triangular prism containing a 8 mm blind hole that stops after 10 mm, in the center.
4. I need a triangular prism with base 60 mm, triangle height 40 mm, and prism height 30 mm, with a centered 8 mm blind hole 10 mm deep.
5. Build a triangular prism (60 mm base, 40 mm height, 30 mm long) with a 8 mm blind hole drilled to 10 mm, in the center.

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
          30.0,
          40.0
        ]
      },
      {
        "id": "e_003",
        "type": "Line",
        "start": [
          30.0,
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
    "length": 30.0
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
          13.333333333333334
        ],
        "radius": 4.0
      }
    ],
    "constraints": [],
    "support": {
      "type": "face",
      "reference": "op_002",
      "selector": "Face5"
    }
  },
  {
    "id": "op_004",
    "type": "Hole",
    "profile": "op_003",
    "diameter": 8.0,
    "depth": 10.0
  }
]
```

