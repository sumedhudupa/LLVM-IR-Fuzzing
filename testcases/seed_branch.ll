; ModuleID = 'seed_branch.ll'
; Test Case 2: Conditional Branching
; Expected exit code: 1  (15 > 12 is true → then branch)
; Tests: icmp predicate change, branch condition flip

define i32 @main() {
entry:
  %x = add i32 5, 10
  %cmp = icmp sgt i32 %x, 12
  br i1 %cmp, label %then, label %else

then:
  ret i32 1

else:
  ret i32 0
}
