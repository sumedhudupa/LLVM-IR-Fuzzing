; ModuleID = 'seed_nested_branch.ll'
; Test Case 7: Nested Conditional Branching
; Expected exit code: 100
;   15 > 12 → outer_then
;   15 - 3 = 12, 12 == 12 → inner_then
;   returns 100
; Tests: nested branch handling, multiple labels, complex CFG

define i32 @main() {
entry:
  %x = add i32 10, 5
  %cmp1 = icmp sgt i32 %x, 12
  br i1 %cmp1, label %outer_then, label %outer_else

outer_then:
  %y = sub i32 %x, 3
  %cmp2 = icmp eq i32 %y, 12
  br i1 %cmp2, label %inner_then, label %inner_else

inner_then:
  ret i32 100

inner_else:
  ret i32 50

outer_else:
  ret i32 0
}
