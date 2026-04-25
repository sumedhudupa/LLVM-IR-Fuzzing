
# Failure Analysis Report

## Overview
- **Total generated**: 145
- **Valid**: 90 (62.1%)
- **Invalid**: 55 (37.9%)

## Validity by Source

### LLM
- Total: 45
- Valid: 37 (82.2%)
- Interesting: 45 (100.0%)

### GRAMMAR
- Total: 50
- Valid: 45 (90.0%)
- Interesting: 27 (54.0%)

### RANDOM
- Total: 50
- Valid: 8 (16.0%)
- Interesting: 7 (14.0%)

## Error Distribution

### broken_control_flow
- Count: 31 (28.4% of errors)
- Example errors: Block 'entry' does not end with a terminator. Last: ']'; Block 'entry': instruction after terminator at position 0

### syntax_error
- Count: 27 (24.8% of errors)
- Example errors: No function definition found (expected 'define <type> @<name>(...)')

### missing_terminator
- Count: 24 (22.0% of errors)
- Example errors: Block 'entry' does not end with a terminator. Last: ']'; Block 'entry': instruction after terminator at position 0

### invalid_phi
- Count: 11 (10.1% of errors)
- Example errors: Block 'positive': instruction after terminator at position 1; Block 'positive': instruction after terminator at position 2

### ssa_violation
- Count: 10 (9.2% of errors)
- Example errors: SSA violation: '%cmp1' defined at line 4 and previously at line 3; LLVM verifier error: LLVM IR parsing error
<string>:4:3: error: multiple definition of local value named 'cmp1'
  %cmp1 = icmp sgt i32 %x, 0
  ^


### unknown
- Count: 4 (3.7% of errors)
- Example errors: LLVM verifier error: LLVM IR parsing error
<string>:3:11: error: use of undefined value '%result'
  ret i32 %result
          ^


### type_mismatch
- Count: 2 (1.8% of errors)
- Example errors: LLVM verifier error: LLVM IR parsing error
<string>:8:10: error: integer constant must have integer type
br label 0
         ^


## Mutation Type Effectiveness
| Mutation Type | Total | Valid | Valid% | Interesting | Avg Time(s) |
|---|---|---|---|---|---|
| from_scratch | 15 | 11 | 73.3% | 15 | 0.000 |
| mutation | 15 | 11 | 73.3% | 15 | 0.000 |
| refinement | 15 | 15 | 100.0% | 15 | 0.000 |
| grammar_swap_operands | 7 | 7 | 100.0% | 4 | 0.000 |
| grammar_change_constant | 5 | 4 | 80.0% | 2 | 0.000 |
| grammar_toggle_overflow_flag | 10 | 8 | 80.0% | 6 | 0.000 |
| grammar_swap_branch_targets | 3 | 3 | 100.0% | 2 | 0.000 |
| grammar_duplicate_instruction | 5 | 5 | 100.0% | 1 | 0.000 |
| grammar_add_nsw_nuw | 7 | 7 | 100.0% | 6 | 0.000 |
| grammar_replace_binop | 2 | 2 | 100.0% | 1 | 0.000 |
| grammar_remove_nsw_nuw | 5 | 4 | 80.0% | 2 | 0.000 |
| grammar_change_icmp_pred | 3 | 3 | 100.0% | 2 | 0.000 |
| grammar_insert_dead_code | 3 | 2 | 66.7% | 1 | 0.000 |
| random_random_char_flip | 9 | 0 | 0.0% | 0 | 0.000 |
| random_random_line_duplicate | 11 | 2 | 18.2% | 2 | 0.000 |
| random_random_line_delete | 13 | 2 | 15.4% | 2 | 0.000 |
| random_random_word_replace | 9 | 0 | 0.0% | 0 | 0.000 |
| random_random_line_swap | 8 | 4 | 50.0% | 3 | 0.000 |

## Semantic Interest Analysis

- Valid IR total: 90
- Semantically interesting: 71 (78.9%)
- Trivial/low-value: 19

## Example Failures

### Failure Example 1 (Source: llm, Type: from_scratch)
**Errors**: missing_terminator, broken_control_flow
**Details**: Block 'entry' does not end with a terminator. Last: ']'; Block 'entry': instruction after terminator at position 0
```llvm
define i32 @switch_250(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %add_case
    i32 1, label %sub_case
    i32 2, label %mul_case
    i32 3, label %div_case
  ]

add_case:
  %r0 = add i32 %a, %b
  br label %done

sub_case:
  %r1 = sub i32 %a, %b
  br label %done

mul_case:
  %r2 = mul i32 %a, %b
  br label %done

div_case:
  %cmp = icmp eq i32 %b, 0
  br i1 %cmp, label %default, label %safe_div

safe_div:
  %r3 = sdiv i32 %a, %b
  br label %done

defaul
```

### Failure Example 2 (Source: llm, Type: from_scratch)
**Errors**: missing_terminator, broken_control_flow
**Details**: Block 'entry' does not end with a terminator. Last: ']'; Block 'entry': instruction after terminator at position 0
```llvm
define i32 @switch_644(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %add_case
    i32 1, label %sub_case
    i32 2, label %mul_case
    i32 3, label %div_case
  ]

add_case:
  %r0 = add i32 %a, %b
  br label %done

sub_case:
  %r1 = sub i32 %a, %b
  br label %done

mul_case:
  %r2 = mul i32 %a, %b
  br label %done

div_case:
  %cmp = icmp eq i32 %b, 0
  br i1 %cmp, label %default, label %safe_div

safe_div:
  %r3 = sdiv i32 %a, %b
  br label %done

defaul
```

### Failure Example 3 (Source: llm, Type: from_scratch)
**Errors**: missing_terminator, broken_control_flow
**Details**: Block 'entry' does not end with a terminator. Last: ']'; Block 'entry': instruction after terminator at position 0
```llvm
define i32 @switch_660(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %add_case
    i32 1, label %sub_case
    i32 2, label %mul_case
    i32 3, label %div_case
  ]

add_case:
  %r0 = add i32 %a, %b
  br label %done

sub_case:
  %r1 = sub i32 %a, %b
  br label %done

mul_case:
  %r2 = mul i32 %a, %b
  br label %done

div_case:
  %cmp = icmp eq i32 %b, 0
  br i1 %cmp, label %default, label %safe_div

safe_div:
  %r3 = sdiv i32 %a, %b
  br label %done

defaul
```

### Failure Example 4 (Source: llm, Type: from_scratch)
**Errors**: missing_terminator, broken_control_flow
**Details**: Block 'entry' does not end with a terminator. Last: ']'; Block 'entry': instruction after terminator at position 0
```llvm
define i32 @switch_285(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %add_case
    i32 1, label %sub_case
    i32 2, label %mul_case
    i32 3, label %div_case
  ]

add_case:
  %r0 = add i32 %a, %b
  br label %done

sub_case:
  %r1 = sub i32 %a, %b
  br label %done

mul_case:
  %r2 = mul i32 %a, %b
  br label %done

div_case:
  %cmp = icmp eq i32 %b, 0
  br i1 %cmp, label %default, label %safe_div

safe_div:
  %r3 = sdiv i32 %a, %b
  br label %done

defaul
```

### Failure Example 5 (Source: llm, Type: mutation)
**Errors**: missing_terminator, broken_control_flow
**Details**: Block 'entry' does not end with a terminator. Last: ']'; Block 'entry': instruction after terminator at position 0
```llvm
define i32 @switch_84(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %add_case
    i32 1, label %sub_case
    i32 2, label %mul_case
    i32 3, label %div_case
  ]

add_case:
  %r0 = add i32 %a, %b
  br label %done

sub_case:
  %r1 = sub i32 %a, %b
  br label %done

mul_case:
  %r2 = mul i32 %a, %b
  br label %done

div_case:
  %cmp = icmp eq i32 %b, 0
  br i1 %cmp, label %default, label %safe_div

safe_div:
  %r3 = sdiv i32 %a, %b
  br label %done

default
```
