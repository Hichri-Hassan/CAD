# Research Log

Date:26 June 2026  
Research Session:\#1

\#\# Objective

What am I trying to answer today?

Data availability

\#\# Initial Hypothesis

What do I currently believe?

There is the data and I should try to find it, I think that I should have an enormous data size so that the LLM can perform well but to get all of that data I might need some help of some agents, we will see

\#\# Research

What did I actually do?

Links  
Repositories  
Papers  
Videos  
Experiments

\---

\#\# Findings

### Major discovery #1 – FCStd is the right data source

Instead of training on STL or meshes, FreeCAD `.FCStd` files preserve the complete parametric history of the model.

A `.FCStd` file is actually a ZIP archive containing:
- Document.xml
- GuiDocument.xml
- *.Shape.brp

The key file is `Document.xml`.

### Major discovery #2 – Understanding Document.xml

The XML is a database of CAD objects.

General hierarchy:

Document
- Objects
- ObjectData

Every feature follows:

Object
- Properties
- Values

Examples:

Sketch
- Geometry
- Constraints
- Plane

Pad
- Profile
- Length

Hole
- Diameter
- Depth

Fillet
- Radius
- Base

Chamfer
- Size
- Angle
- Base

### Major discovery #3 – Dependency graph

FreeCAD stores the dependency graph automatically.

Body
- Sketch
- Pad
- Sketch001
- Hole

### Major discovery #4 – V1 scope

Support only:
- Sketch
- Pad
- Pocket
- Hole
- Fillet
- Chamfer

### Major discovery #5 – Parser philosophy

The parser extracts only the properties required by the generator.

### Major discovery #6 – New architecture

Prompt
↓
LLM
↓
CAD JSON (our DSL)
↓
Compiler
↓
FreeCAD Python API
↓
FCStd / STEP

The LLM generates JSON, not Python.

What did I discover?

\---

\#\# Evidence

Screenshots  
Links  
Examples  
Numbers

\---

\#\# Conclusions

What can I confidently conclude?


The project is now divided into four modules:

1. Parser (FCStd -> JSON)
2. Dataset (JSON operations)
3. LLM (Prompt -> JSON)
4. Compiler (JSON -> FreeCAD API)

\---

\#\# New Questions

What new questions appeared?

\---

\#\# Decisions

Did I change anything about the project?

- FCStd is the canonical dataset.
- Ignore advanced operations for V1.
- Create a CAD JSON specification first.
- Parser only supports V1 operations.

\---

\#\# Next Session

What is the next thing I should investigate?

1. Finalize JSON schema.
2. Build parser.
3. Parse Sketch, Pad, Hole.
4. Add Pocket, Fillet, Chamfer.
5. Test on many FCStd files.


\---

\#\# Personal Thoughts

Anything interesting?  the .FCStd has different files, it should be interesting to make sure that all of these files work well when building the project + when the AI will generate the .STEP
Ideas?  
Possible startup opportunities?  



### Open Question

Should the compiler generate a `.FCStd` file directly, or should it simply execute the FreeCAD Python API and let FreeCAD generate the entire project structure automatically?

If the second approach works reliably, it would significantly simplify the compiler.


