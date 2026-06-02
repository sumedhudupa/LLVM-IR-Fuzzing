; ModuleID = 'seed_loop.ll'
; Test Case 3: Loop with PHI Nodes
; Expected exit code: 10  (sum of 0+1+2+3+4 = 10)
; Tests: PHI node handling, loop structure, SSA compliance

define i32 @main() {
entry:
  br label %loop

loop:
  %i = phi i32 [ 0, %entry ], [ %next, %loop ]
  %sum = phi i32 [ 0, %entry ], [ %newsum, %loop ]
  %newsum = add i32 %sum, %i
  %next = add i32 %i, 1
  %cond = icmp slt i32 %next, 5
  br i1 %cond, label %loop, label %exit

exit:
  ret i32 %newsum
}
