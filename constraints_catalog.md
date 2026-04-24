# Catalog of LLVM IR Validity Constraints

## 1. Static Single Assignment (SSA) Form

### 1.1 Single Definition Rule
Every virtual register (`%name` or `%N`) must be defined exactly once in the
entire function. Re-assignment to the same register name is illegal.

**Valid:**
```llvm
%x = add i32 %a, %b
%y = mul i32 %x, 2
```

**Invalid (SSA violation):**
```llvm
%x = add i32 %a, %b
%x = mul i32 %x, 2    ; ERROR: %x defined twice
```

### 1.2 Definition Must Dominate All Uses
Every use of a value must be dominated by its definition — meaning the definition
must execute before any possible path to the use. This is the dominance property.

**Invalid (use before def):**
```llvm
entry:
  br label %loop

loop:
  %v = add i32 %w, 1   ; ERROR: %w not yet defined (if first iteration)
  %w = phi i32 [0, %entry], [%v, %loop]
```

### 1.3 PHI Node Placement
PHI nodes must appear at the beginning of a basic block, before any non-PHI
instructions. They merge values from predecessor blocks.

**Constraints:**
- PHI nodes must list exactly the predecessor blocks of their parent block
- Each predecessor must appear exactly once in the PHI node
- Types of incoming values must match the PHI's type
- PHI nodes cannot appear in the entry block (it has no predecessors)

**Valid:**
```llvm
merge:
  %result = phi i32 [%a, %then_bb], [%b, %else_bb]
  ret i32 %result
```

**Invalid:**
```llvm
merge:
  %x = add i32 1, 2
  %result = phi i32 [%a, %then_bb], [%b, %else_bb]  ; ERROR: PHI after non-PHI
```

## 2. Type System Constraints

### 2.1 Strict Type Matching
LLVM IR is strongly typed. All operands must have matching types, and there
are no implicit conversions.

**Integer types:** `i1`, `i8`, `i16`, `i32`, `i64`, `i128`
**Float types:** `half`, `float`, `double`, `fp128`
**Pointer type:** `ptr` (opaque pointers in modern LLVM)
**Vector types:** `<4 x i32>`, `<2 x float>`
**Aggregate types:** `{ i32, float }` (struct), `[10 x i32]` (array)

**Invalid (type mismatch):**
```llvm
%x = add i32 %a, %b      ; %a is i32
%y = fadd float %x, 1.0   ; ERROR: %x is i32, not float
```

### 2.2 Instruction-Type Compatibility
Each instruction constrains operand types:
- `add`, `sub`, `mul`, `sdiv`, `udiv`, `srem`, `urem`: integer or integer vector
- `fadd`, `fsub`, `fmul`, `fdiv`, `frem`: floating point or fp vector
- `and`, `or`, `xor`, `shl`, `lshr`, `ashr`: integer or integer vector
- `icmp`: integer operands, returns `i1`
- `fcmp`: floating-point operands, returns `i1`

### 2.3 Cast Instructions Must Be Valid
- `trunc`: integer to smaller integer
- `zext`/`sext`: integer to larger integer
- `fptrunc`/`fpext`: float conversions
- `fptoui`/`fptosi`: float to integer
- `uitofp`/`sitofp`: integer to float
- `bitcast`: same-size reinterpretation (restricted in modern LLVM)
- `ptrtoint`/`inttoptr`: pointer ↔ integer

### 2.4 GEP (GetElementPtr) Constraints
GEP requires:
- First operand must be a pointer
- Index types must be integers
- Index structure must match the pointed-to type's nesting
- Result type is always a pointer

## 3. Control Flow Constraints

### 3.1 Terminator Instructions
Every basic block must end with exactly one terminator instruction:
- `ret` — return from function
- `br` — unconditional or conditional branch
- `switch` — multi-way branch
- `invoke` — call that may throw (unwind)
- `resume` — resume propagation of exception
- `unreachable` — undefined behavior marker
- `indirectbr` — indirect branch

**Invalid (no terminator):**
```llvm
entry:
  %x = add i32 1, 2
  ; ERROR: block does not end with terminator
```

**Invalid (instruction after terminator):**
```llvm
entry:
  ret i32 0
  %x = add i32 1, 2    ; ERROR: unreachable code after terminator
```

### 3.2 Branch Targets Must Be Valid
All branch targets must reference existing basic blocks within the same function.

### 3.3 Entry Block
The first basic block in a function is the entry block. Control flow starts here.
No other block may branch to the entry block (in well-formed IR — the verifier
actually allows this but PHI nodes in entry are forbidden).

### 3.4 Reachability
Unreachable blocks are technically valid LLVM IR but semantically useless for
testing. The verifier does not reject them, but they add no coverage value.

## 4. Function and Module Structure

### 4.1 Function Signature Constraints
- Return type must match all `ret` instructions
- Parameter types must match call site arguments
- Calling convention must be consistent
- Variable arguments (`...`) require specific handling

### 4.2 Global Variables
- Must have a type and optional initializer
- Constant globals need `constant` keyword
- Thread-local globals need `thread_local`

### 4.3 Declarations vs Definitions
- External functions: `declare i32 @printf(ptr, ...)`
- Defined functions: `define i32 @main() { ... }`
- All called functions must be declared or defined

### 4.4 Module-Level Requirements
- `target datalayout` — optional but recommended
- `target triple` — optional but recommended
- Global variable declarations before function definitions

## 5. Memory and Pointer Constraints

### 5.1 Load/Store Type Matching
```llvm
%ptr = alloca i32           ; allocates i32-sized memory
store i32 42, ptr %ptr      ; OK: storing i32 to i32 alloca
%val = load i32, ptr %ptr   ; OK: loading i32 from i32 alloca
%bad = load i64, ptr %ptr   ; TECHNICALLY VALID but may be UB
```

### 5.2 Alloca Placement
`alloca` should be in the entry block for efficient stack frame layout.
While `alloca` in non-entry blocks is valid, it creates dynamic stack allocations.

### 5.3 Alignment
`align N` on load/store/alloca must be a power of 2.

## 6. Semantic Constraints (Beyond Syntax)

### 6.1 Poison Values
Operations that produce mathematically undefined results create poison values:
- Division by zero with `nuw`/`nsw` flags
- Overflow with `nuw` (no unsigned wrap) or `nsw` (no signed wrap)
- Out-of-range shift amounts

Poison propagates through operations. Using poison in a side-effecting operation
(store, branch condition) is undefined behavior.

### 6.2 Undef Values
`undef` represents an arbitrary bit pattern. Each use of `undef` may independently
take any value of its type. Key distinction from poison:
- `undef` is a non-deterministic value
- `poison` is a deferred UB marker

### 6.3 Undefined Behavior (UB)
Common sources in LLVM IR:
- Null pointer dereference
- Use-after-free
- Stack buffer overflow
- Signed integer overflow (when `nsw` flag is set)
- Misaligned memory access
- Data race in concurrent contexts

### 6.4 `noundef` Attribute
Marks a value that must not be `undef` or `poison`. Violating this is immediate UB.

### 6.5 Memory Model Constraints
- `atomic` operations require ordering constraints
- `fence` instructions have specific semantics
- `volatile` loads/stores cannot be reordered by the optimizer

## 7. Optimization-Relevant Constraints

### 7.1 nsw/nuw Flags
`add nsw i32 %a, %b` — no signed wrap: if the addition overflows (signed), result
is poison. These flags are critical for optimizer reasoning:
- With `nsw`: optimizer can assume no overflow → enables more transforms
- Without: optimizer must be conservative

### 7.2 exact Flag
`sdiv exact i32 %a, %b` — result is poison if division is not exact (has remainder).

### 7.3 Fast-Math Flags
`fadd fast float %a, %b` — allows reassociation, NaN/Inf assumptions:
- `nnan` — no NaN inputs/outputs
- `ninf` — no infinity inputs/outputs
- `nsz` — no signed zero
- `arcp` — allow reciprocal approximation
- `contract` — allow fused multiply-add
- `afn` — approximate functions
- `reassoc` — allow reassociation
- `fast` — all of the above

### 7.4 Memory Attributes
- `readonly` — function does not modify memory
- `readnone` — function does not read or modify memory
- `argmemonly` — function only accesses argument-pointed memory
- `willreturn` — function always returns
- `nounwind` — function does not throw exceptions
- `mustprogress` — function makes observable progress (no infinite loops without side effects)

## 8. Common LLM Failure Modes

Based on literature (Cummins et al. 2023, Jiang et al. 2025, Xia et al. 2023):

| Failure Mode | Frequency | Description |
|---|---|---|
| SSA Violation | Very High | Re-assigning to same register name |
| Type Mismatch | Very High | Mixing i32/i64/float without casts |
| Missing Terminator | High | Basic blocks without ret/br |
| Invalid PHI | High | Wrong predecessor list, PHI after non-PHI |
| Use Before Def | Medium | Referencing undefined registers |
| Invalid Opcode | Medium | Using non-existent instructions |
| Wrong Argument Count | Medium | Call with wrong number of arguments |
| Missing Function Decl | Medium | Calling undeclared external functions |
| Broken Control Flow | Medium | Branch to nonexistent block |
| Semantically Useless | High | Valid IR that exercises no interesting paths |

## 9. Constraints Checklist for LLM-Generated IR

- [ ] Every register assigned exactly once (SSA)
- [ ] Every use dominated by its definition
- [ ] PHI nodes at block start only
- [ ] PHI predecessors match actual CFG predecessors
- [ ] All types match in operations
- [ ] All casts are valid direction (e.g., trunc to smaller)
- [ ] Every block has exactly one terminator at the end
- [ ] No instructions after terminators
- [ ] All branch targets are valid block labels
- [ ] Function return type matches ret instructions
- [ ] All called functions are declared
- [ ] Call arguments match function parameter types
- [ ] GEP indices are valid for the pointed-to type
- [ ] Alignment values are powers of 2
- [ ] nsw/nuw/exact flags used only on valid instructions
- [ ] Memory operations have valid pointer operands
