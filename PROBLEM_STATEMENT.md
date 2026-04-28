Can LLMs Generate Valid LLVM IR Test Cases for Differential Compiler Testing?
Description: Explore whether an LLM can generate or mutate semantically valid LLVM IR
test cases for compiler differential testing, and study how such outputs can be filtered,
validated, and compared against traditional fuzzing approaches.
Background: LLVM already has strong testing and fuzzing infrastructure, and tools such as
Csmith, YARPGen, and coverage-guided fuzzers have shown real value in finding compiler
bugs. But generating useful LLVM IR is still difficult. LLVM IR is constrained by strict
typing, SSA form, dominance rules, PHI correctness, and subtle semantics such as poison,
undef, and undefined behavior. Most naive mutations become invalid IR, meaningless tests,
or low-value cases that do not explore new optimizer behavior.
The concern, then, is not that LLVM “cannot test itself,” but that high-quality IR test
generation remains a hard problem. Existing fuzzers can also become biased or saturate
around certain patterns. This makes the topic a strong paper-driven project: the hard part is
not producing text, but producing IR mutations that are valid, semantically interesting, and
actually useful for differential testing.
Objective: Build a workflow where students:
(a) study existing compiler testing and fuzzing methods such as Csmith, YARPGen, and
coverage-guided mutation,
(b) identify the structural constraints required for valid LLVM IR mutation,
(c) prompt an LLM to generate or mutate LLVM IR test cases,
(d) filter the outputs using verifier-based, rule-based, or semantic checks, and
(e) evaluate where LLM-based generation helps, fails, or adds no value compared to
grammar-based fuzzing.
Deliverables:
• A short survey of compiler fuzzing and differential testing methods relevant to LLVM
• A catalog of LLVM IR validity constraints the LLM must satisfy
• A small prototype workflow for LLM-guided IR mutation and filtering
• A study of failure cases such as broken SSA, type errors, invalid PHIs, and
semantically useless mutations

• A comparison between LLM-based mutation and traditional grammar/random
mutation approaches
• A report answering: Can LLMs generate useful LLVM IR tests beyond existing
fuzzing methods, or do they mostly produce invalid or low-value cases?
• A final presentation with examples, evaluation criteria, observations, and lessons
learned