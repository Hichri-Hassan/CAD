# 				Literature Review


CAD-LLM: Large Language Model for CAD Generation

Authors: Autodesk Research

Publication: NeurIPS 2023 Workshop

Paper: https://www.research.autodesk.com/app/uploads/2024/05/cadllm_neurips2023_workshop-1.pdf

⸻

Notes / Critical Analysis

Fine-tuning comparison with GPT-3.5

The comparison with GPT-3.5 is not entirely fair. Due to the computational cost of fine-tuning, GPT-3.5 was only trained on 1%, 7% and 15% of the available training dataset, whereas the T5-based CAD-LLM was trained on the complete dataset. Therefore, the reported GPT-3.5 results may underestimate the actual capabilities of large language models under equivalent training conditions.

⸻

Continuous-to-discrete representation

The model converts continuous geometric parameters into discrete values using 6-bit uniform quantization. While this representation simplifies sequence prediction for transformer models, it introduces approximation errors. Small geometric deviations caused by quantization may reduce geometric precision and make it more difficult to preserve exact geometric relationships required in parametric CAD systems.

⸻

Evaluation metrics

The proposed evaluation metrics (Entity Accuracy, Sketch Accuracy and CAD F1) measure the similarity between the generated sketch and the reference sketch. However, they do not evaluate whether the generated sketches are actually valid CAD models.

The paper does not verify whether generated sketches:

* satisfy geometric constraints,
* remain fully parametric,
* can be reconstructed successfully by a CAD kernel,
* can be converted into manufacturable 3D models.

For practical CAD applications, these aspects are as important as geometric similarity.

⸻

Limited model comparison

The experimental evaluation is limited to three models (Vitruvion, GPT-3.5 and T5-based CAD-LLM). Although sufficient to validate the proposed approach, evaluating a broader range of language models would provide a more comprehensive comparison.

⸻

Scope of the work

The proposed approach focuses on 2D sketch autocompletion rather than complete parametric CAD generation. The model predicts sketch entities such as lines, circles and arcs, but does not generate higher-level CAD operations including feature trees, extrusions, revolutions, fillets or chamfers. Consequently, the paper addresses only a subset of the overall Text-to-CAD problem.




SketchGraphs: A Large-Scale Dataset for Modeling Relational Geometry in Computer-Aided Design

Authors: Ari Seff, Yaniv Ovadia, Wenda Zhou, Ryan P. Adams

Publication: arXiv 2020

Paper: https://arxiv.org/abs/2007.08506

⸻

Notes / Critical Analysis

Scope of the work

The proposed approach is restricted to 2D sketch modeling and geometric constraint prediction. Although sketches are a fundamental component of parametric CAD, they represent only the first stage of the design process. The paper does not model higher-level CAD operations such as extrusions, pockets, revolutions, fillets or chamfers. Consequently, the work addresses only a subset of the complete Text-to-CAD problem.

⸻

Limited practical applicability

The generated outputs remain 2D sketches rather than complete executable CAD models. While the proposed tasks are useful for sketch assistance, they cannot directly produce editable parametric parts that can be modified or manufactured using standard CAD workflows.

⸻

Experimental contribution

Although the paper introduces a large-scale dataset containing 15 million sketches, the experimental evaluation is limited to sketch generation and constraint prediction. Several additional applications discussed throughout the paper are presented as future work but are not experimentally validated, making the overall contribution feel narrower than initially suggested.
