<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# explain me the roblem statement. I didnt understand what they are asking to solve, to implement

Great question. Let’s break down the **problem statement** in plain, simple terms so you clearly see **what you are asked to solve and implement**.

***

### 🎯 What the assignment is really asking

You are asked to **build a small research‑style prototype** that answers this question:

> **“Can a Large Language Model (LLM, like Qwen3 or Gemma via Ollama) generate LLVM IR test cases that are *valid* and *useful* for differential testing, compared with traditional fuzzers?”**

In other words:

- Right now, tools like `Csmith`, `YARPGen`, and coverage‑guided fuzzers generate **C code → LLVM IR**, but generating **good LLVM IR directly** is hard because of strict rules (SSA, PHI, types, etc.).
- You will use an **LLM (through Ollama)** to **create or mutate** LLVM IR files.
- Then you must **check** whether the LLM‑generated IR is **valid** and **semantically meaningful** (not junk).
- Finally, you **run differential tests** on those IR files and **compare** LLM‑based generation with traditional fuzzing (grammar‑based mutation).

This is a “paper‑style” project: the **hard part is not code volume**, but **designing and evaluating** the workflow.

***

### 🔍 Step‑by‑step in plain English

Think of your prototype as a **pipeline** with 4 clear stages:

#### 1. **Seed IR and existing fuzzers** (Study, not implement from scratch)

- You:
    - Take **existing LLVM IR files** (`.ll`) as **seeds** (e.g., from simple C programs compiled with `clang -S -emit-llvm`).
    - Study tools like **Csmith**, **YARPGen**, and **coverage‑guided fuzzers** to understand how they generate tests (this is for the **survey**).


#### 2. **LLM‑guided LLVM IR mutation** (Your main implementation)

- You:
    - Read a seed LLVM IR file (text).
    - Send it to the **LLM** (via Ollama) with a prompt like:
> “Mutate this LLVM IR by changing instructions, loops, or function calls, keeping SSA, types, and PHI rules valid.”
    - The LLM returns a **mutated `.ll` file** (LLM‑generated mutant).
    - Repeat this for multiple seeds and generate many mutants.


#### 3. **Filtering and validation** (Your “cleaner” step)

- You:
    - Run each mutant through **LLVM’s built‑in checks**:
        - `llvm-as` → checks basic syntax.
        - `opt -verify` → checks SSA, types, CFG, PHI, etc.
    - If it passes, the mutant **goes into the “valid”** bucket.
    - If it fails, you **log** why (e.g., “broken SSA”, “type error”, etc.).


#### 4. **Differential testing and comparison** (Your “evaluation”)

- You:
    - Compile each **valid** LLVM IR with different options:
        - `llc -O0` (baseline),
        - `llc -O2` (optimized),
        - or compare two different LLVM backends (e.g., x86 vs AArch64).
    - Run programs (or harnesses) for both versions and **compare behavior**:
        - Do they produce the same result?
        - Does one crash where the other doesn’t?
        - Is there a **performance** or **correctness** mismatch?
    - Finally, you **compare**:
        - How many **valid** mutants the LLM produced vs a **grammar‑based fuzzer** (e.g., IRFuzzer‑style).
        - How many **bugs / mismatches** were found in each case.

***

### 🧩 What you are *expected to implement* (concretely)

You don’t need to build a full compiler or fuzzing framework; you are expected to prototype a **well‑defined loop**:

1. **Inputs**:
    - Seed `.ll` files.
    - An LLM hosted via Ollama (e.g., `ollama serve` + `qwen3:1.5b`).
2. **Core pipeline**:
    - A script that:

3. **Generates LLM‑mutated LLVM IR** (one mutant per seed, or N mutants per seed).
4. **Saves mutants** to disk (e.g., `mutants_llm/...ll`).
5. **Validates** mutants with `llvm-as` + `opt -verify`.
6. **Classifies** as valid/invalid and logs errors.
7. **Runs differential tests** (O0 vs O2) on valid mutants.
8. **Collects data**: validity rate, failure types, bug‑finding rate.
1. **Comparison**:
    - Optionally, you can add a **grammar‑based mutator** (very simple IR‑level edits, like IRFuzzer‑style) and compare:
        - How many valid mutants each method produces.
        - How many differential bugs each finds.
2. **Outputs**:
    - A **short survey** on compiler‑testing tools (Csmith, YARPGen, IRFuzzer, etc.).
    - A **catalog** of LLVM IR constraints (SSA, PHI, types, etc.).
    - A **prototype** (Python + shell scripts) that runs the above loop.
    - A **table** or **report** answering:
*“Can LLMs generate useful LLVM IR tests beyond existing fuzzing methods, or do they mostly produce invalid or low‑value cases?”*

***

### 🧠 Simple analogy

Think of it like this:

- **Traditional fuzzers** = **random mutation machine** that tweaks LLVM IR based on grammar rules.
- **Your LLM‑based tool** = **“smart” mutation machine** that tries to change IR in more meaningful, high‑level ways.
- Your job is to:
    - Build a **small machine** (your Dockerized pipeline),
    - Feed it **seeds**,
    - See **how often it generates valid, bug‑finding IR**,
    - And **compare** it to the “random” machine.

***

### ✅ What you don’t need to do

- You **don’t** need to:
    - Implement a full‑blown compiler.
    - Fix any LLVM bugs you find.
    - Build a fancy GUI at this stage (CLI + Docker is fine).
- You **do** need to:
    - Have a **clear, reproducible pipeline**.
    - Show **numbers** (validity rate, bug‑finding rate, failure types).

***

### 💡 In one sentence

**You are implementing an AI‑powered, LLVM‑IR‑mutation pipeline that uses an LLM to generate test cases, validates them with LLVM tools, runs differential tests, and compares its usefulness against traditional grammar‑based fuzzing.**

If you tell me exactly which part feels fuzziest (e.g., “LLM‑guidance vs grammar‑based mutation” or “differential testing harness”), I can break that into a **line‑by‑line pseudo‑code plan** you can translate directly into Python or shell.

