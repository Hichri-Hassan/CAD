# Prompts and Generated Responses

From final model evaluation (2026-07-31T14:07:55.064186+00:00)

## model_0009

### Prompt (user input)

> Create a prismatic solid with milled features.

### Generated response (raw)

```
{"operations":[{"id":"op_001","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[0.0,0.0],"end":[83.0,0.0]},{"id":"e_002","type":"Line","start":[83.0,0.0],"end":[97.475,39.771]},{"id":"e_003","type":"Line","start":[97.475,39.771],"end":[88.078,43.191]},{"id":"e_004","type":"Line","start":[88.078,43.191],"end":[77.818,15.0]},{"id":"e_005","type":"Line","start":[77.818,15.0],"end":[17.818,15.0]},{"id":"e_006","type":"Line","start":[17.818,15.0],"end":[2.449,42.727]},{"id":"e_007","type":"Line","start":[2.449,42.727],"end":[12.615,70.657]},{"id":"e_008","type":"Line","start":[12.615,70.657],"end":[3.218,74.077]},{"id":"e_009","type":"Line","start":[3.218,74.077],"end":[-10.463,36.489]},{"id":"e_010","type":"Line","start":[-10.463,36.489],"end":[0.0,0.0]}],"constraints":[],"plane":"XY"},{"id":"op_002","type":"Pad","profile":"op_001","length":5.0},{"id":"op_003","type":"Sketch","entities":[{"id":"e_001","type":"Circle","center":[91.067,36.782],"radius":1.25},{"id":"e_002","type":"Circle","center":[84.226,17.988],"radius":1.25},{"id":"e_003","type":"Circle","center":[6.206,67.669],"radius":1.25},{"id":"e_004","type":"Circle","center":[1.076,53.573],"radius":1.25},{"id":"e_005","type":"Circle","center":[68.0,5.0],"radius":1.25},{"id":"e_006","type":"Circle","center":[33.0,5.0],"radius":1.25}],"constraints":[],"plane":"XY"},{"id":"op_004","type":"Pocket","profile":"op_003","depth":5.0}]}
```

### Generated response (formatted JSON)

```json
{
  "operations": [
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
            83.0,
            0.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            83.0,
            0.0
          ],
          "end": [
            97.475,
            39.771
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            97.475,
            39.771
          ],
          "end": [
            88.078,
            43.191
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            88.078,
            43.191
          ],
          "end": [
            77.818,
            15.0
          ]
        },
        {
          "id": "e_005",
          "type": "Line",
          "start": [
            77.818,
            15.0
          ],
          "end": [
            17.818,
            15.0
          ]
        },
        {
          "id": "e_006",
          "type": "Line",
          "start": [
            17.818,
            15.0
          ],
          "end": [
            2.449,
            42.727
          ]
        },
        {
          "id": "e_007",
          "type": "Line",
          "start": [
            2.449,
            42.727
          ],
          "end": [
            12.615,
            70.657
          ]
        },
        {
          "id": "e_008",
          "type": "Line",
          "start": [
            12.615,
            70.657
          ],
          "end": [
            3.218,
            74.077
          ]
        },
        {
          "id": "e_009",
          "type": "Line",
          "start": [
            3.218,
            74.077
          ],
          "end": [
            -10.463,
            36.489
          ]
        },
        {
          "id": "e_010",
          "type": "Line",
          "start": [
            -10.463,
            36.489
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
            91.067,
            36.782
          ],
          "radius": 1.25
        },
        {
          "id": "e_002",
          "type": "Circle",
          "center": [
            84.226,
            17.988
          ],
          "radius": 1.25
        },
        {
          "id": "e_003",
          "type": "Circle",
          "center": [
            6.206,
            67.669
          ],
          "radius": 1.25
        },
        {
          "id": "e_004",
          "type": "Circle",
          "center": [
            1.076,
            53.573
          ],
          "radius": 1.25
        },
        {
          "id": "e_005",
          "type": "Circle",
          "center": [
            68.0,
            5.0
          ],
          "radius": 1.25
        },
        {
          "id": "e_006",
          "type": "Circle",
          "center": [
            33.0,
            5.0
          ],
          "radius": 1.25
        }
      ],
      "constraints": [],
      "plane": "XY"
    },
    {
      "id": "op_004",
      "type": "Pocket",
      "profile": "op_003",
      "depth": 5.0
    }
  ]
}
```

- JSON valid: True | Schema valid: True | Op-type accuracy: 66.7% | Ops: 4/6

---

## model_0015

### Prompt (user input)

> Create a prismatic solid with milled features.

### Generated response (raw)

```
{"operations":[{"id":"op_001","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[-5.25,0.0],"end":[5.25,0.0]},{"id":"e_002","type":"Line","start":[5.25,0.0],"end":[5.25,3.75]},{"id":"e_003","type":"Line","start":[5.25,3.75],"end":[3.0,3.75]},{"id":"e_004","type":"Line","start":[3.0,3.75],"end":[3.0,5.0]},{"id":"e_005","type":"Line","start":[3.0,5.0],"end":[-3.0,5.0]},{"id":"e_006","type":"Line","start":[-3.0,5.0],"end":[-3.0,3.75]},{"id":"e_007","type":"Line","start":[-3.0,3.75],"end":[-5.25,3.75]},{"id":"e_008","type":"Line","start":[-5.25,3.75],"end":[-5.25,0.0]}],"constraints":[],"plane":"XY"},{"id":"op_002","type":"Pad","profile":"op_001","length":10.5,"symmetric":true},{"id":"op_003","type":"Fillet","radius":0.3,"edges":[{"reference":"op_002","selector":"Edge1"},{"reference":"op_002","selector":"Edge2"},{"reference":"op_002","selector":"Edge5"},{"reference":"op_002","selector":"Edge8"},{"reference":"op_002","selector":"Edge11"},{"reference":"op_002","selector":"Edge14"},{"reference":"op_002","selector":"Edge21"},{"reference":"op_002","selector":"Edge17"}]},{"id":"op_004","type":"Sketch","entities":[{"id":"e_001","type":"Circle","center":[0.0,0.0],"radius":1.0}],"constraints":[],"plane":"XY"},{"id":"op_005","type":"Pocket","profile":"op_004","depth":10.5,"reversed":true},{"id":"op_006","type":"Fillet","radius":0.3,"edges":[{"reference":"op_005","selector":"Edge2"},{"reference":"op_005","selector":"Edge5"},{"reference":"op_005","selector":"Edge8"},{"reference":"op_005","selector":"Edge1"},{"reference":"op_005","selector":"Edge14"},{"reference":"op_005","selector":"Edge21"},{"reference":"op_005","selector":"Edge17"},{"reference":"op_005","selector":"Edge19"}]}]}
```

### Generated response (formatted JSON)

```json
{
  "operations": [
    {
      "id": "op_001",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Line",
          "start": [
            -5.25,
            0.0
          ],
          "end": [
            5.25,
            0.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            5.25,
            0.0
          ],
          "end": [
            5.25,
            3.75
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            5.25,
            3.75
          ],
          "end": [
            3.0,
            3.75
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            3.0,
            3.75
          ],
          "end": [
            3.0,
            5.0
          ]
        },
        {
          "id": "e_005",
          "type": "Line",
          "start": [
            3.0,
            5.0
          ],
          "end": [
            -3.0,
            5.0
          ]
        },
        {
          "id": "e_006",
          "type": "Line",
          "start": [
            -3.0,
            5.0
          ],
          "end": [
            -3.0,
            3.75
          ]
        },
        {
          "id": "e_007",
          "type": "Line",
          "start": [
            -3.0,
            3.75
          ],
          "end": [
            -5.25,
            3.75
          ]
        },
        {
          "id": "e_008",
          "type": "Line",
          "start": [
            -5.25,
            3.75
          ],
          "end": [
            -5.25,
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
      "length": 10.5,
      "symmetric": true
    },
    {
      "id": "op_003",
      "type": "Fillet",
      "radius": 0.3,
      "edges": [
        {
          "reference": "op_002",
          "selector": "Edge1"
        },
        {
          "reference": "op_002",
          "selector": "Edge2"
        },
        {
          "reference": "op_002",
          "selector": "Edge5"
        },
        {
          "reference": "op_002",
          "selector": "Edge8"
        },
        {
          "reference": "op_002",
          "selector": "Edge11"
        },
        {
          "reference": "op_002",
          "selector": "Edge14"
        },
        {
          "reference": "op_002",
          "selector": "Edge21"
        },
        {
          "reference": "op_002",
          "selector": "Edge17"
        }
      ]
    },
    {
      "id": "op_004",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Circle",
          "center": [
            0.0,
            0.0
          ],
          "radius": 1.0
        }
      ],
      "constraints": [],
      "plane": "XY"
    },
    {
      "id": "op_005",
      "type": "Pocket",
      "profile": "op_004",
      "depth": 10.5,
      "reversed": true
    },
    {
      "id": "op_006",
      "type": "Fillet",
      "radius": 0.3,
      "edges": [
        {
          "reference": "op_005",
          "selector": "Edge2"
        },
        {
          "reference": "op_005",
          "selector": "Edge5"
        },
        {
          "reference": "op_005",
          "selector": "Edge8"
        },
        {
          "reference": "op_005",
          "selector": "Edge1"
        },
        {
          "reference": "op_005",
          "selector": "Edge14"
        },
        {
          "reference": "op_005",
          "selector": "Edge21"
        },
        {
          "reference": "op_005",
          "selector": "Edge17"
        },
        {
          "reference": "op_005",
          "selector": "Edge19"
        }
      ]
    }
  ]
}
```

- JSON valid: True | Schema valid: True | Op-type accuracy: 33.3% | Ops: 6/6

---

## model_0016

### Prompt (user input)

> Create a prismatic solid with milled features.

### Generated response (raw)

```
{"operations":[{"id":"op_001","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[0.0,0.0],"end":[90.0,0.0]},{"id":"e_002","type":"Line","start":[0.0,0.0],"end":[0.0,30.0]},{"id":"e_003","type":"Line","start":[0.0,30.0],"end":[5.0,30.0]},{"id":"e_004","type":"Line","start":[5.0,30.0],"end":[5.0,40.0]},{"id":"e_005","type":"Line","start":[5.0,40.0],"end":[85.0,40.0]},{"id":"e_006","type":"Line","start":[85.0,40.0],"end":[85.0,30.0]},{"id":"e_007","type":"Line","start":[85.0,30.0],"end":[90.0,30.0]},{"id":"e_008","type":"Line","start":[90.0,30.0],"end":[90.0,0.0]},{"id":"e_009","type":"Line","start":[27.5,30.0],"end":[32.5,30.0]},{"id":"e_010","type":"Line","start":[32.5,30.0],"end":[32.5,10.0]},{"id":"e_011","type":"Line","start":[32.5,10.0],"end":[27.5,10.0]},{"id":"e_012","type":"Line","start":[27.5,10.0],"end":[27.5,30.0]},{"id":"e_013","type":"Line","start":[37.5,30.0],"end":[42.5,30.0]},{"id":"e_014","type":"Line","start":[42.5,30.0],"end":[42.5,10.0]},{"id":"e_015","type":"Line","start":[42.5,10.0],"end":[37.5,10.0]},{"id":"e_016","type":"Line","start":[37.5,10.0],"end":[37.5,30.0]},{"id":"e_017","type":"Line","start":[47.5,30.0],"end":[52.5,30.0]},{"id":"e_018","type":"Line","start":[52.5,30.0],"end":[52.5,10.0]},{"id":"e_019","type":"Line","start":[52.5,10.0],"end":[47.5,10.0]},{"id":"e_020","type":"Line","start":[47.5,10.0],"end":[47.5,30.0]},{"id":"e_021","type":"Line","start":[57.5,30.0],"end":[62.5,30.0]},{"id":"e_022","type":"Line","start":[62.5,30.0],"end":[62.5,10.0]},{"id":"e_023","type":"Line","start":[62.5,10.0],"end":[57.5,10.0]},{"id":"e_024","type":"Line","start":[57.5,10.0],"end":[57.5,30.0]}],"constraints":[],"plane":"XY"},{"id":"op_002","type":"Pad","profile":"op_001","length":20.0},{"id":"op_003","type":"Sketch","entities":[{"id":"e_001","type":"Circle","center":[10.0,10.0],"radius":5.0},{"id":"e_002","type":"Circle","center":[80.0,10.0],"radius":5.0}],"constraints":[],"plane":"XY"},{"id":"op_004","type":"Pocket","profile":"op_003","depth":2.5},{"id":"op_005","type":"Chamfer","distance":1.25,"edges":[{"reference":"op_004","selector":"Edge21"},{"reference":"op_004","selector":"Edge20"}]},{"id":"op_006","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[10.0,35.0],"end":[80.0,35.0]},{"id":"e_002","type":"Line","start":[80.0,35.0],"end":[80.0,5.0]},{"id":"e_003","type":"Line","start":[80.0,5.0],"end":[10.0,5.0]},{"id":"e_004","type":"Line","start":[10.0,5.0],"end":[10.0,35.0]},{"id":"e_005","type":"Line","start":[30.0,15.0],"end":[60.0,15.0]},{"id":"e_006","type":"Line","start":[60.0,15.0],"end":[60.0,5.0]},{"id":"e_007","type":"Line","start":[60.0,5.0],"end":[30.0,5.0]},{"id":"e_008","type":"Line","start":[30.0,5.0],"end":[30.0,15.0]},{"id":"e_009","type":"Circle","center":[5.0,5.0],"radius":1.25},{"id":"e_010","type":"Circle","center":[85.0,5.0],"radius":1.25}],"constraints":[],"plane":"XY"},{"id":"op_007","type":"Pocket","profile":"op_006","depth":2.5}]}
```

### Generated response (formatted JSON)

```json
{
  "operations": [
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
            90.0,
            0.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            0.0,
            0.0
          ],
          "end": [
            0.0,
            30.0
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            0.0,
            30.0
          ],
          "end": [
            5.0,
            30.0
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            5.0,
            30.0
          ],
          "end": [
            5.0,
            40.0
          ]
        },
        {
          "id": "e_005",
          "type": "Line",
          "start": [
            5.0,
            40.0
          ],
          "end": [
            85.0,
            40.0
          ]
        },
        {
          "id": "e_006",
          "type": "Line",
          "start": [
            85.0,
            40.0
          ],
          "end": [
            85.0,
            30.0
          ]
        },
        {
          "id": "e_007",
          "type": "Line",
          "start": [
            85.0,
            30.0
          ],
          "end": [
            90.0,
            30.0
          ]
        },
        {
          "id": "e_008",
          "type": "Line",
          "start": [
            90.0,
            30.0
          ],
          "end": [
            90.0,
            0.0
          ]
        },
        {
          "id": "e_009",
          "type": "Line",
          "start": [
            27.5,
            30.0
          ],
          "end": [
            32.5,
            30.0
          ]
        },
        {
          "id": "e_010",
          "type": "Line",
          "start": [
            32.5,
            30.0
          ],
          "end": [
            32.5,
            10.0
          ]
        },
        {
          "id": "e_011",
          "type": "Line",
          "start": [
            32.5,
            10.0
          ],
          "end": [
            27.5,
            10.0
          ]
        },
        {
          "id": "e_012",
          "type": "Line",
          "start": [
            27.5,
            10.0
          ],
          "end": [
            27.5,
            30.0
          ]
        },
        {
          "id": "e_013",
          "type": "Line",
          "start": [
            37.5,
            30.0
          ],
          "end": [
            42.5,
            30.0
          ]
        },
        {
          "id": "e_014",
          "type": "Line",
          "start": [
            42.5,
            30.0
          ],
          "end": [
            42.5,
            10.0
          ]
        },
        {
          "id": "e_015",
          "type": "Line",
          "start": [
            42.5,
            10.0
          ],
          "end": [
            37.5,
            10.0
          ]
        },
        {
          "id": "e_016",
          "type": "Line",
          "start": [
            37.5,
            10.0
          ],
          "end": [
            37.5,
            30.0
          ]
        },
        {
          "id": "e_017",
          "type": "Line",
          "start": [
            47.5,
            30.0
          ],
          "end": [
            52.5,
            30.0
          ]
        },
        {
          "id": "e_018",
          "type": "Line",
          "start": [
            52.5,
            30.0
          ],
          "end": [
            52.5,
            10.0
          ]
        },
        {
          "id": "e_019",
          "type": "Line",
          "start": [
            52.5,
            10.0
          ],
          "end": [
            47.5,
            10.0
          ]
        },
        {
          "id": "e_020",
          "type": "Line",
          "start": [
            47.5,
            10.0
          ],
          "end": [
            47.5,
            30.0
          ]
        },
        {
          "id": "e_021",
          "type": "Line",
          "start": [
            57.5,
            30.0
          ],
          "end": [
            62.5,
            30.0
          ]
        },
        {
          "id": "e_022",
          "type": "Line",
          "start": [
            62.5,
            30.0
          ],
          "end": [
            62.5,
            10.0
          ]
        },
        {
          "id": "e_023",
          "type": "Line",
          "start": [
            62.5,
            10.0
          ],
          "end": [
            57.5,
            10.0
          ]
        },
        {
          "id": "e_024",
          "type": "Line",
          "start": [
            57.5,
            10.0
          ],
          "end": [
            57.5,
            30.0
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
            10.0,
            10.0
          ],
          "radius": 5.0
        },
        {
          "id": "e_002",
          "type": "Circle",
          "center": [
            80.0,
            10.0
          ],
          "radius": 5.0
        }
      ],
      "constraints": [],
      "plane": "XY"
    },
    {
      "id": "op_004",
      "type": "Pocket",
      "profile": "op_003",
      "depth": 2.5
    },
    {
      "id": "op_005",
      "type": "Chamfer",
      "distance": 1.25,
      "edges": [
        {
          "reference": "op_004",
          "selector": "Edge21"
        },
        {
          "reference": "op_004",
          "selector": "Edge20"
        }
      ]
    },
    {
      "id": "op_006",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Line",
          "start": [
            10.0,
            35.0
          ],
          "end": [
            80.0,
            35.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            80.0,
            35.0
          ],
          "end": [
            80.0,
            5.0
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            80.0,
            5.0
          ],
          "end": [
            10.0,
            5.0
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            10.0,
            5.0
          ],
          "end": [
            10.0,
            35.0
          ]
        },
        {
          "id": "e_005",
          "type": "Line",
          "start": [
            30.0,
            15.0
          ],
          "end": [
            60.0,
            15.0
          ]
        },
        {
          "id": "e_006",
          "type": "Line",
          "start": [
            60.0,
            15.0
          ],
          "end": [
            60.0,
            5.0
          ]
        },
        {
          "id": "e_007",
          "type": "Line",
          "start": [
            60.0,
            5.0
          ],
          "end": [
            30.0,
            5.0
          ]
        },
        {
          "id": "e_008",
          "type": "Line",
          "start": [
            30.0,
            5.0
          ],
          "end": [
            30.0,
            15.0
          ]
        },
        {
          "id": "e_009",
          "type": "Circle",
          "center": [
            5.0,
            5.0
          ],
          "radius": 1.25
        },
        {
          "id": "e_010",
          "type": "Circle",
          "center": [
            85.0,
            5.0
          ],
          "radius": 1.25
        }
      ],
      "constraints": [],
      "plane": "XY"
    },
    {
      "id": "op_007",
      "type": "Pocket",
      "profile": "op_006",
      "depth": 2.5
    }
  ]
}
```

- JSON valid: True | Schema valid: True | Op-type accuracy: 50.0% | Ops: 7/8

---

## model_0018

### Prompt (user input)

> Create a prismatic solid with milled features.

### Generated response (raw)

```
{"operations":[{"id":"op_001","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[0.0,0.0],"end":[900.0,0.0]},{"id":"e_002","type":"Line","start":[900.0,0.0],"end":[900.0,550.0]},{"id":"e_003","type":"Line","start":[900.0,550.0],"end":[0.0,550.0]},{"id":"e_004","type":"Line","start":[0.0,550.0],"end":[0.0,0.0]}],"constraints":[],"plane":"XY"},{"id":"op_002","type":"Pad","profile":"op_001","length":120.0},{"id":"op_003","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[300.0,550.0],"end":[600.0,550.0]},{"id":"e_002","type":"Line","start":[600.0,550.0],"end":[600.0,150.0]},{"id":"e_003","type":"Line","start":[600.0,150.0],"end":[300.0,150.0]},{"id":"e_004","type":"Line","start":[300.0,150.0],"end":[300.0,550.0]}],"constraints":[],"plane":"XY"},{"id":"op_004","type":"Pocket","profile":"op_003","depth":50.0},{"id":"op_005","type":"Chamfer","distance":25.0,"edges":[{"reference":"op_004","selector":"Edge7"}]},{"id":"op_006","type":"Chamfer","distance":25.0,"edges":[{"reference":"op_005","selector":"Edge4"}]}]}
```

### Generated response (formatted JSON)

```json
{
  "operations": [
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
            900.0,
            0.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            900.0,
            0.0
          ],
          "end": [
            900.0,
            550.0
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            900.0,
            550.0
          ],
          "end": [
            0.0,
            550.0
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            0.0,
            550.0
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
      "length": 120.0
    },
    {
      "id": "op_003",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Line",
          "start": [
            300.0,
            550.0
          ],
          "end": [
            600.0,
            550.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            600.0,
            550.0
          ],
          "end": [
            600.0,
            150.0
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            600.0,
            150.0
          ],
          "end": [
            300.0,
            150.0
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            300.0,
            150.0
          ],
          "end": [
            300.0,
            550.0
          ]
        }
      ],
      "constraints": [],
      "plane": "XY"
    },
    {
      "id": "op_004",
      "type": "Pocket",
      "profile": "op_003",
      "depth": 50.0
    },
    {
      "id": "op_005",
      "type": "Chamfer",
      "distance": 25.0,
      "edges": [
        {
          "reference": "op_004",
          "selector": "Edge7"
        }
      ]
    },
    {
      "id": "op_006",
      "type": "Chamfer",
      "distance": 25.0,
      "edges": [
        {
          "reference": "op_005",
          "selector": "Edge4"
        }
      ]
    }
  ]
}
```

- JSON valid: True | Schema valid: True | Op-type accuracy: 50.0% | Ops: 6/8

---

## model_0002

### Prompt (user input)

> Create a extruded prismatic solid.

### Generated response (raw)

```
{"operations":[{"id":"op_001","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[-5.25,0.0],"end":[5.25,0.0]},{"id":"e_002","type":"Line","start":[5.25,0.0],"end":[5.25,3.75]},{"id":"e_003","type":"Line","start":[5.25,3.75],"end":[3.0,3.75]},{"id":"e_004","type":"Line","start":[3.0,3.75],"end":[3.0,5.0]},{"id":"e_005","type":"Line","start":[3.0,5.0],"end":[-3.0,5.0]},{"id":"e_006","type":"Line","start":[-3.0,5.0],"end":[-3.0,3.75]},{"id":"e_007","type":"Line","start":[-3.0,3.75],"end":[-5.25,3.75]},{"id":"e_008","type":"Line","start":[-5.25,3.75],"end":[-5.25,0.0]}],"constraints":[],"plane":"XY"},{"id":"op_002","type":"Pad","profile":"op_001","length":10.5,"reversed":true}]}
```

### Generated response (formatted JSON)

```json
{
  "operations": [
    {
      "id": "op_001",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Line",
          "start": [
            -5.25,
            0.0
          ],
          "end": [
            5.25,
            0.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            5.25,
            0.0
          ],
          "end": [
            5.25,
            3.75
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            5.25,
            3.75
          ],
          "end": [
            3.0,
            3.75
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            3.0,
            3.75
          ],
          "end": [
            3.0,
            5.0
          ]
        },
        {
          "id": "e_005",
          "type": "Line",
          "start": [
            3.0,
            5.0
          ],
          "end": [
            -3.0,
            5.0
          ]
        },
        {
          "id": "e_006",
          "type": "Line",
          "start": [
            -3.0,
            5.0
          ],
          "end": [
            -3.0,
            3.75
          ]
        },
        {
          "id": "e_007",
          "type": "Line",
          "start": [
            -3.0,
            3.75
          ],
          "end": [
            -5.25,
            3.75
          ]
        },
        {
          "id": "e_008",
          "type": "Line",
          "start": [
            -5.25,
            3.75
          ],
          "end": [
            -5.25,
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
      "length": 10.5,
      "reversed": true
    }
  ]
}
```

- JSON valid: True | Schema valid: True | Op-type accuracy: 66.7% | Ops: 2/3

---

## model_0008

### Prompt (user input)

> Create a prismatic solid with milled features.

### Generated response (raw)

```
{"operations":[{"id":"op_001","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[-5.25,0.0],"end":[5.25,0.0]},{"id":"e_002","type":"Line","start":[5.25,0.0],"end":[5.25,3.75]},{"id":"e_003","type":"Line","start":[5.25,3.75],"end":[3.0,3.75]},{"id":"e_004","type":"Line","start":[3.0,3.75],"end":[3.0,5.0]},{"id":"e_005","type":"Line","start":[3.0,5.0],"end":[-3.0,5.0]},{"id":"e_006","type":"Line","start":[-3.0,5.0],"end":[-3.0,3.75]},{"id":"e_007","type":"Line","start":[-3.0,3.75],"end":[-5.25,3.75]},{"id":"e_008","type":"Line","start":[-5.25,3.75],"end":[-5.25,0.0]}],"constraints":[],"plane":"XY"},{"id":"op_002","type":"Pad","profile":"op_001","length":10.5,"symmetric":true},{"id":"op_003","type":"Fillet","radius":0.3,"edges":[{"reference":"op_002","selector":"Edge1"},{"reference":"op_002","selector":"Edge2"},{"reference":"op_002","selector":"Edge3"},{"reference":"op_002","selector":"Edge4"},{"reference":"op_002","selector":"Edge5"},{"reference":"op_002","selector":"Edge6"},{"reference":"op_002","selector":"Edge7"},{"reference":"op_002","selector":"Edge8"}]},{"id":"op_004","type":"Sketch","entities":[{"id":"e_001","type":"Circle","center":[0.0,0.0],"radius":1.0}],"constraints":[],"plane":"XY"},{"id":"op_005","type":"Pocket","profile":"op_004","depth":10.5,"reversed":true},{"id":"op_006","type":"Fillet","radius":0.3,"edges":[{"reference":"op_005","selector":"Edge21"},{"reference":"op_005","selector":"Edge22"},{"reference":"op_005","selector":"Edge23"},{"reference":"op_005","selector":"Edge25"},{"reference":"op_005","selector":"Edge27"},{"reference":"op_005","selector":"Edge29"},{"reference":"op_005","selector":"Edge32"}]}]}
```

### Generated response (formatted JSON)

```json
{
  "operations": [
    {
      "id": "op_001",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Line",
          "start": [
            -5.25,
            0.0
          ],
          "end": [
            5.25,
            0.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            5.25,
            0.0
          ],
          "end": [
            5.25,
            3.75
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            5.25,
            3.75
          ],
          "end": [
            3.0,
            3.75
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            3.0,
            3.75
          ],
          "end": [
            3.0,
            5.0
          ]
        },
        {
          "id": "e_005",
          "type": "Line",
          "start": [
            3.0,
            5.0
          ],
          "end": [
            -3.0,
            5.0
          ]
        },
        {
          "id": "e_006",
          "type": "Line",
          "start": [
            -3.0,
            5.0
          ],
          "end": [
            -3.0,
            3.75
          ]
        },
        {
          "id": "e_007",
          "type": "Line",
          "start": [
            -3.0,
            3.75
          ],
          "end": [
            -5.25,
            3.75
          ]
        },
        {
          "id": "e_008",
          "type": "Line",
          "start": [
            -5.25,
            3.75
          ],
          "end": [
            -5.25,
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
      "length": 10.5,
      "symmetric": true
    },
    {
      "id": "op_003",
      "type": "Fillet",
      "radius": 0.3,
      "edges": [
        {
          "reference": "op_002",
          "selector": "Edge1"
        },
        {
          "reference": "op_002",
          "selector": "Edge2"
        },
        {
          "reference": "op_002",
          "selector": "Edge3"
        },
        {
          "reference": "op_002",
          "selector": "Edge4"
        },
        {
          "reference": "op_002",
          "selector": "Edge5"
        },
        {
          "reference": "op_002",
          "selector": "Edge6"
        },
        {
          "reference": "op_002",
          "selector": "Edge7"
        },
        {
          "reference": "op_002",
          "selector": "Edge8"
        }
      ]
    },
    {
      "id": "op_004",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Circle",
          "center": [
            0.0,
            0.0
          ],
          "radius": 1.0
        }
      ],
      "constraints": [],
      "plane": "XY"
    },
    {
      "id": "op_005",
      "type": "Pocket",
      "profile": "op_004",
      "depth": 10.5,
      "reversed": true
    },
    {
      "id": "op_006",
      "type": "Fillet",
      "radius": 0.3,
      "edges": [
        {
          "reference": "op_005",
          "selector": "Edge21"
        },
        {
          "reference": "op_005",
          "selector": "Edge22"
        },
        {
          "reference": "op_005",
          "selector": "Edge23"
        },
        {
          "reference": "op_005",
          "selector": "Edge25"
        },
        {
          "reference": "op_005",
          "selector": "Edge27"
        },
        {
          "reference": "op_005",
          "selector": "Edge29"
        },
        {
          "reference": "op_005",
          "selector": "Edge32"
        }
      ]
    }
  ]
}
```

- JSON valid: True | Schema valid: True | Op-type accuracy: 33.3% | Ops: 6/6

---

## model_0041

### Prompt (user input)

> Create a extruded prismatic solid.

### Generated response (raw)

```
{"operations":[{"id":"op_001","type":"Sketch","entities":[{"id":"e_001","type":"Line","start":[-5.25,0.0],"end":[5.25,0.0]},{"id":"e_002","type":"Line","start":[5.25,0.0],"end":[5.25,3.75]},{"id":"e_003","type":"Line","start":[5.25,3.75],"end":[3.0,3.75]},{"id":"e_004","type":"Line","start":[3.0,3.75],"end":[3.0,5.0]},{"id":"e_005","type":"Line","start":[3.0,5.0],"end":[-3.0,5.0]},{"id":"e_006","type":"Line","start":[-3.0,5.0],"end":[-3.0,3.75]},{"id":"e_007","type":"Line","start":[-3.0,3.75],"end":[-5.25,3.75]},{"id":"e_008","type":"Line","start":[-5.25,3.75],"end":[-5.25,0.0]}],"constraints":[],"plane":"XY"},{"id":"op_002","type":"Pad","profile":"op_001","length":10.5,"reversed":true}]}
```

### Generated response (formatted JSON)

```json
{
  "operations": [
    {
      "id": "op_001",
      "type": "Sketch",
      "entities": [
        {
          "id": "e_001",
          "type": "Line",
          "start": [
            -5.25,
            0.0
          ],
          "end": [
            5.25,
            0.0
          ]
        },
        {
          "id": "e_002",
          "type": "Line",
          "start": [
            5.25,
            0.0
          ],
          "end": [
            5.25,
            3.75
          ]
        },
        {
          "id": "e_003",
          "type": "Line",
          "start": [
            5.25,
            3.75
          ],
          "end": [
            3.0,
            3.75
          ]
        },
        {
          "id": "e_004",
          "type": "Line",
          "start": [
            3.0,
            3.75
          ],
          "end": [
            3.0,
            5.0
          ]
        },
        {
          "id": "e_005",
          "type": "Line",
          "start": [
            3.0,
            5.0
          ],
          "end": [
            -3.0,
            5.0
          ]
        },
        {
          "id": "e_006",
          "type": "Line",
          "start": [
            -3.0,
            5.0
          ],
          "end": [
            -3.0,
            3.75
          ]
        },
        {
          "id": "e_007",
          "type": "Line",
          "start": [
            -3.0,
            3.75
          ],
          "end": [
            -5.25,
            3.75
          ]
        },
        {
          "id": "e_008",
          "type": "Line",
          "start": [
            -5.25,
            3.75
          ],
          "end": [
            -5.25,
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
      "length": 10.5,
      "reversed": true
    }
  ]
}
```

- JSON valid: True | Schema valid: True | Op-type accuracy: 66.7% | Ops: 2/3

---
